package middleware

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
	siteapp "github.com/dujiao-next/internal/modules/site/application"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/gin-gonic/gin"
)

type visitGeoEntry struct {
	region  string
	expires time.Time
}

var visitGeoCache = struct {
	sync.Mutex
	items map[string]visitGeoEntry
}{items: make(map[string]visitGeoEntry)}

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
			if strings.TrimSpace(p) == "" {
				p = c.Request.URL.Path
			}
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
		if key, _ := c.Cookie("gpn_visit"); len(key) != 64 {
			var b [32]byte
			if _, err := rand.Read(b[:]); err == nil {
				c.SetSameSite(http.SameSiteLaxMode)
				c.SetCookie("gpn_visit", hex.EncodeToString(b[:]), 86400*90, "/", "", c.Request.TLS != nil || c.Request.Header.Get("X-Forwarded-Proto") == "https", true)
			}
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
		clientIP := strings.TrimSpace(c.ClientIP())
		if clientIP == "" {
			clientIP = "unknown"
		}
		bucket := now.Truncate(60 * time.Minute).UTC().Format(time.RFC3339)
		hash := sha256.Sum256([]byte(clientIP + "|" + bucket))
		_ = s.Store.RecordVisit(sitedomain.Visit{SiteID: tenant.SourceSiteID, Domain: tenant.Host, Day: now.In(loc).Format("2006-01-02"), VisitorHash: hex.EncodeToString(hash[:]), ClientIP: clientIP, Region: visitRegion(clientIP), UserID: c.GetUint("user_id"), FirstSeenAt: now, LastSeenAt: now})
	}
}

func visitRegion(raw string) string {
	ip := net.ParseIP(strings.TrimSpace(raw))
	if ip == nil {
		return "未知地区"
	}
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast() {
		return "内网"
	}
	key := ip.String()
	now := time.Now()
	visitGeoCache.Lock()
	if entry, ok := visitGeoCache.items[key]; ok && now.Before(entry.expires) {
		visitGeoCache.Unlock()
		return entry.region
	}
	visitGeoCache.Unlock()

	region := "公网（地区未解析）"
	ctx, cancel := context.WithTimeout(context.Background(), 800*time.Millisecond)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://ipapi.co/"+key+"/json/", nil)
	if err == nil {
		if resp, requestErr := http.DefaultClient.Do(req); requestErr == nil {
			defer resp.Body.Close()
			if resp.StatusCode >= 200 && resp.StatusCode < 300 {
				var payload struct {
					CountryName string `json:"country_name"`
					Region      string `json:"region"`
					City        string `json:"city"`
				}
				if json.NewDecoder(resp.Body).Decode(&payload) == nil {
					parts := make([]string, 0, 3)
					for _, part := range []string{payload.CountryName, payload.Region, payload.City} {
						if value := strings.TrimSpace(part); value != "" {
							parts = append(parts, value)
						}
					}
					if len(parts) > 0 {
						region = strings.Join(parts, " · ")
					}
				}
			}
		}
	}
	visitGeoCache.Lock()
	visitGeoCache.items[key] = visitGeoEntry{region: region, expires: now.Add(24 * time.Hour)}
	visitGeoCache.Unlock()
	return region
}
