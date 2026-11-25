package domain

import "time"

// Site is an operator-owned storefront. Domains are immutable and never reused.
type Site struct {
	ID                     uint      `gorm:"primarykey" json:"id"`
	Name                   string    `gorm:"size:100;not null" json:"name"`
	Domain                 string    `gorm:"size:253;uniqueIndex;not null" json:"domain"`
	Enabled                bool      `gorm:"not null;default:true" json:"enabled"`
	CreatedAt              time.Time `json:"created_at"`
	UpdatedAt              time.Time `json:"updated_at"`
	CertificateStatus      string    `gorm:"-" json:"certificate_status,omitempty"`
	CertificateExpiresAt   string    `gorm:"-" json:"certificate_expires_at,omitempty"`
	CertificateError       string    `gorm:"-" json:"certificate_error,omitempty"`
	CertificateRequestedAt string    `gorm:"-" json:"certificate_requested_at,omitempty"`
}

func (Site) TableName() string { return "storefront_sites" }

// AdminScope survives removal of all grants so revocation fails closed.
type AdminScope struct {
	AdminID   uint      `gorm:"primarykey" json:"admin_id"`
	UpdatedAt time.Time `json:"updated_at"`
}

func (AdminScope) TableName() string { return "storefront_admin_scopes" }

type Grant struct {
	AdminID        uint `gorm:"primarykey" json:"admin_id"`
	SiteID         uint `gorm:"primarykey" json:"site_id"`
	Overview       bool `json:"overview"`
	Users          bool `json:"users"`
	Orders         bool `json:"orders"`
	Visits         bool `json:"visits"`
	ProductCatalog bool `json:"product_catalog"`
}

func (Grant) TableName() string { return "storefront_admin_grants" }

// Visit aggregates requests from the same IP for a short window per site.
type Visit struct {
	ID          uint      `gorm:"primarykey" json:"id"`
	SiteID      uint      `gorm:"uniqueIndex:idx_site_visit,priority:1;index" json:"site_id"`
	Domain      string    `gorm:"size:253" json:"domain"`
	Day         string    `gorm:"size:10;uniqueIndex:idx_site_visit,priority:2;index" json:"day"`
	VisitorHash string    `gorm:"size:64;uniqueIndex:idx_site_visit,priority:3" json:"-"`
	UserID      uint      `gorm:"index;uniqueIndex:idx_site_visit,priority:4" json:"user_id,omitempty"`
	UserEmail   string    `gorm:"-" json:"user_email,omitempty"`
	ClientIP    string    `gorm:"size:64;index" json:"client_ip,omitempty"`
	Region      string    `gorm:"size:160" json:"region,omitempty"`
	FirstSeenAt time.Time `json:"first_seen_at"`
	LastSeenAt  time.Time `json:"last_seen_at"`
}

func (Visit) TableName() string { return "storefront_visits" }

type Scope struct {
	Restricted bool    `json:"restricted"`
	Grants     []Grant `json:"grants"`
}

func (s Scope) Allows(siteID uint, menu string) bool {
	if !s.Restricted {
		return true
	}
	for _, g := range s.Grants {
		if g.SiteID != siteID {
			continue
		}
		switch menu {
		case "overview":
			return g.Overview
		case "users":
			return g.Users
		case "orders":
			return g.Orders
		case "visits":
			return g.Visits
		case "product_catalog":
			return g.ProductCatalog
		}
	}
	return false
}

func (s Scope) AllowsAny(menu string) bool {
	if !s.Restricted {
		return true
	}
	for _, g := range s.Grants {
		if menu == "product_catalog" && g.ProductCatalog {
			return true
		}
	}
	return false
}
