package application

import (
	"context"
	"errors"
	"net"
	"net/http"
	"strings"

	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
	sitecontract "github.com/dujiao-next/internal/modules/site/contract"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
)

var ErrInvalid = errors.New("invalid site or administrator grant")

type Resolver interface {
	ResolveRequest(context.Context, *http.Request) (resellercontract.TenantContext, error)
}
type Service struct {
	Store      sitecontract.Store
	BaseDomain string
	Fallback   Resolver
}

func New(store sitecontract.Store, base string, fallback Resolver) *Service {
	base = resellercontract.NormalizeHost(base)
	if base == "" {
		base = "gptpaynow.com"
	}
	return &Service{Store: store, BaseDomain: base, Fallback: fallback}
}
func NormalizeDomain(raw string) (string, error) {
	host := resellercontract.NormalizeHost(raw)
	if len(host) > 253 || !strings.Contains(host, ".") || strings.ContainsAny(host, "/:@?#%\\ \t\n\r") || net.ParseIP(host) != nil {
		return "", ErrInvalid
	}
	for _, label := range strings.Split(host, ".") {
		if len(label) == 0 || len(label) > 63 || label[0] == '-' || label[len(label)-1] == '-' {
			return "", ErrInvalid
		}
		for _, r := range label {
			if !(r >= 'a' && r <= 'z' || r >= '0' && r <= '9' || r == '-') {
				return "", ErrInvalid
			}
		}
	}
	return host, nil
}

// Host is deliberately read from the connection, never a user-supplied origin header.
func (s *Service) ResolveRequest(ctx context.Context, req *http.Request) (resellercontract.TenantContext, error) {
	host := resellercontract.NormalizeHost(req.Host)
	// Reserved main-service hosts never depend on the site directory. Adding or
	// disabling a campus site must not affect the main storefront/payment flow.
	if host == s.BaseDomain || host == "www."+s.BaseDomain || host == "pay."+s.BaseDomain {
		return resellercontract.MainTenantContext(host), nil
	}
	site, err := s.Store.FindDomain(host)
	if err != nil {
		return resellercontract.TenantContext{}, err
	}
	if site != nil {
		if !site.Enabled {
			return resellercontract.UnavailableTenantContext(host, "disabled"), nil
		}
		t := resellercontract.MainTenantContext(host)
		t.SourceSiteID = site.ID
		return t, nil
	}
	if s.Fallback != nil {
		// The reverse proxy must preserve Host. Forwarded headers are not an
		// authority for attribution, including in the legacy reseller resolver.
		trustedRequest := req.Clone(ctx)
		trustedRequest.Header.Del("X-Forwarded-Host")
		tenant, err := s.Fallback.ResolveRequest(ctx, trustedRequest)
		if err != nil || tenant.IsReseller() || tenant.Unavailable {
			return tenant, err
		}
		if strings.HasSuffix(host, "."+s.BaseDomain) && host != "www."+s.BaseDomain && host != "pay."+s.BaseDomain {
			return resellercontract.UnavailableTenantContext(host, "unregistered"), nil
		}
		return tenant, nil
	}
	if strings.HasSuffix(host, "."+s.BaseDomain) && host != "www."+s.BaseDomain && host != "pay."+s.BaseDomain {
		return resellercontract.UnavailableTenantContext(host, "unregistered"), nil
	}
	return resellercontract.MainTenantContext(host), nil
}
func (s *Service) SaveSite(site *sitedomain.Site) error {
	site.Name = strings.TrimSpace(site.Name)
	if site.Name == "" || len([]rune(site.Name)) > 100 {
		return ErrInvalid
	}
	if site.ID == 0 {
		domain, err := NormalizeDomain(site.Domain)
		if err != nil {
			return err
		}
		label := strings.TrimSuffix(domain, "."+s.BaseDomain)
		if domain == s.BaseDomain || label == domain || strings.Contains(label, ".") || label == "www" || label == "api" || label == "pay" || label == "admin" {
			return ErrInvalid
		}
		taken, err := s.Store.DomainInUse(domain)
		if err != nil {
			return err
		}
		if taken {
			return ErrInvalid
		}
		site.Domain = domain
	}
	return s.Store.SaveSite(site)
}
func (s *Service) SetGrants(adminID uint, grants []sitedomain.Grant) error {
	valid, err := s.Store.AdminExists(adminID)
	if err != nil {
		return err
	}
	if !valid {
		return ErrInvalid
	}
	sites, err := s.Store.ListSites()
	if err != nil {
		return err
	}
	ids := map[uint]bool{}
	for _, site := range sites {
		ids[site.ID] = true
	}
	seen := map[uint]bool{}
	for i, g := range grants {
		if !ids[g.SiteID] || seen[g.SiteID] {
			return ErrInvalid
		}
		seen[g.SiteID] = true
		grants[i].AdminID = adminID
	}
	return s.Store.SetGrants(adminID, grants)
}
