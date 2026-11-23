package middleware

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"net/http"
	"strings"
	"time"

	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
	siteapp "github.com/dujiao-next/internal/modules/site/application"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/gin-gonic/gin"
)

// SiteAdminMiddleware is evaluated on every request so revocations are immediate.
// Scoped admins can never fall through to legacy global resource endpoints.
func SiteAdminMiddleware(s *siteapp.Service) gin.HandlerFunc {
	return func(c *gin.Context) {
		if c.GetBool("admin_is_super") {
			c.Next()
			return
		}
		scope, err := s.Store.GetScope(c.GetUint("admin_id"))
		if err != nil {
			response.ErrorWithHTTPStatus(c, 500, response.CodeInternal, "Unable to resolve administrator scope")
			return
		}
		c.Set("site_scope", scope)
		if scope.Restricted {
			p := c.FullPath()
			if strings.HasPrefix(p, "/api/v1/admin/product-catalog") && !scope.AllowsAny("product_catalog") {
				response.ErrorWithHTTPStatus(c, 403, response.CodeForbidden, "Product catalog is not authorized")
				return
			}
			if !(strings.HasPrefix(p, "/api/v1/admin/site-console/") || strings.HasPrefix(p, "/api/v1/admin/product-catalog") || p == "/api/v1/admin/authz/me" || p == "/api/v1/admin/password" || strings.HasPrefix(p, "/api/v1/admin/2fa")) {
				response.ErrorWithHTTPStatus(c, 403, response.CodeForbidden, "Use the authorized site console")
				return
			}
		}
		c.Next()
	}
}

// SiteVisitMiddleware runs after tenant resolution, even on public browsing.
func SiteVisitMiddleware(s *siteapp.Service) gin.HandlerFunc {
	return func(c *gin.Context) {
		tenant, ok := resellercontract.TenantFromContext(c.Request.Context())
		if !ok || tenant.SourceSiteID == 0 {
			c.Next()
			return
		}
		key, _ := c.Cookie("gpn_visit")
		if len(key) != 64 {
			var b [32]byte
			if _, err := rand.Read(b[:]); err == nil {
				key = hex.EncodeToString(b[:])
				c.SetSameSite(http.SameSiteLaxMode)
				c.SetCookie("gpn_visit", key, 86400*90, "/", "", c.Request.TLS != nil || c.Request.Header.Get("X-Forwarded-Proto") == "https", true)
			}
		}
		if len(key) != 64 {
			c.Next()
			return
		}
		c.Next()
		if c.Writer.Status() >= 400 {
			return
		}
		now := time.Now()
		loc, _ := time.LoadLocation("Asia/Shanghai")
		if loc == nil {
			loc = time.FixedZone("Asia/Shanghai", 8*3600)
		}
		hash := sha256.Sum256([]byte(key))
		_ = s.Store.RecordVisit(sitedomain.Visit{SiteID: tenant.SourceSiteID, Domain: tenant.Host, Day: now.In(loc).Format("2006-01-02"), VisitorHash: hex.EncodeToString(hash[:]), UserID: c.GetUint("user_id"), FirstSeenAt: now, LastSeenAt: now})
	}
}
