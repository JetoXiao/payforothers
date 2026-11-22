package application

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
)

func TestRequestCertificateWritesPendingRequestAndDecoratesSite(t *testing.T) {
	dir := t.TempDir()
	t.Setenv("SITE_CERT_REQUEST_DIR", dir)
	site := &sitedomain.Site{ID: 42, Domain: "test.gptpaynow.com"}
	if err := RequestCertificate(site); err != nil {
		t.Fatal(err)
	}
	status := ReadCertificateStatus(site.ID)
	if status.State != certificateStatePending || status.Domain != site.Domain {
		t.Fatalf("unexpected status: %+v", status)
	}
	files, err := filepath.Glob(filepath.Join(dir, "request-42-*.json"))
	if err != nil || len(files) != 1 {
		t.Fatalf("expected one request file, files=%v err=%v", files, err)
	}
	data, err := os.ReadFile(files[0])
	if err != nil {
		t.Fatal(err)
	}
	var request struct {
		SiteID uint   `json:"site_id"`
		Domain string `json:"domain"`
	}
	if err := json.Unmarshal(data, &request); err != nil || request.SiteID != site.ID || request.Domain != site.Domain {
		t.Fatalf("unexpected request: %s err=%v", data, err)
	}
	DecorateCertificate(site)
	if site.CertificateStatus != certificateStatePending {
		t.Fatalf("expected decorated pending status, got %q", site.CertificateStatus)
	}
}
