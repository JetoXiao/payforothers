package application

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
)

const (
	certificateStatePending = "pending"
	certificateStateUnknown = "not_requested"
)

type CertificateStatus struct {
	State       string `json:"state"`
	Domain      string `json:"domain"`
	ExpiresAt   string `json:"expires_at,omitempty"`
	Error       string `json:"error,omitempty"`
	RequestedAt string `json:"requested_at,omitempty"`
	UpdatedAt   string `json:"updated_at,omitempty"`
}

func certificateRequestDir() string {
	if value := strings.TrimSpace(os.Getenv("SITE_CERT_REQUEST_DIR")); value != "" {
		return value
	}
	return "/app/cert-requests"
}

func certificateStatusPath(siteID uint) string {
	return filepath.Join(certificateRequestDir(), "status", strconv.FormatUint(uint64(siteID), 10)+".json")
}

func ReadCertificateStatus(siteID uint) CertificateStatus {
	status := CertificateStatus{State: certificateStateUnknown}
	data, err := os.ReadFile(certificateStatusPath(siteID))
	if err != nil {
		return status
	}
	if json.Unmarshal(data, &status) != nil || strings.TrimSpace(status.State) == "" {
		return CertificateStatus{State: certificateStateUnknown}
	}
	return status
}

func DecorateCertificate(site *sitedomain.Site) {
	if site == nil {
		return
	}
	status := ReadCertificateStatus(site.ID)
	site.CertificateStatus = status.State
	site.CertificateExpiresAt = status.ExpiresAt
	site.CertificateError = status.Error
	site.CertificateRequestedAt = status.RequestedAt
}

func RequestCertificate(site *sitedomain.Site) error {
	if site == nil || site.ID == 0 || strings.TrimSpace(site.Domain) == "" {
		return ErrInvalid
	}
	status := ReadCertificateStatus(site.ID)
	if status.State == certificateStatePending || status.State == "issuing" {
		return errors.New("certificate request already pending")
	}
	if err := os.MkdirAll(filepath.Join(certificateRequestDir(), "status"), 0o750); err != nil {
		return err
	}
	nonceBytes := make([]byte, 12)
	if _, err := rand.Read(nonceBytes); err != nil {
		return err
	}
	now := time.Now().UTC().Format(time.RFC3339)
	status = CertificateStatus{State: certificateStatePending, Domain: site.Domain, RequestedAt: now, UpdatedAt: now}
	if err := writeJSONAtomic(certificateStatusPath(site.ID), status); err != nil {
		return err
	}
	request := struct {
		SiteID      uint   `json:"site_id"`
		Domain      string `json:"domain"`
		RequestedAt string `json:"requested_at"`
	}{SiteID: site.ID, Domain: site.Domain, RequestedAt: now}
	requestPath := filepath.Join(certificateRequestDir(), "request-"+strconv.FormatUint(uint64(site.ID), 10)+"-"+hex.EncodeToString(nonceBytes)+".json")
	if err := writeJSONAtomic(requestPath, request); err != nil {
		return err
	}
	return nil
}

func writeJSONAtomic(path string, value any) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	tmp := path + ".tmp-" + strconv.FormatInt(time.Now().UnixNano(), 10)
	if err := os.WriteFile(tmp, data, 0o640); err != nil {
		return err
	}
	if err := os.Rename(tmp, path); err != nil {
		_ = os.Remove(tmp)
		return err
	}
	return nil
}
