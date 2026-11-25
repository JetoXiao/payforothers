package integrationtest

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dujiao-next/internal/app/httpserver/middleware"
	"github.com/dujiao-next/internal/authz"
	"github.com/dujiao-next/internal/config"
	"github.com/dujiao-next/internal/constants"
	admindomain "github.com/dujiao-next/internal/modules/identity/admin/domain"
	userdomain "github.com/dujiao-next/internal/modules/identity/user/domain"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	paymentdomain "github.com/dujiao-next/internal/modules/payment/domain"
	productcatalogdomain "github.com/dujiao-next/internal/modules/productcatalog/domain"
	resellerapp "github.com/dujiao-next/internal/modules/reseller/application"

	siteapp "github.com/dujiao-next/internal/modules/site/application"
	sitecontract "github.com/dujiao-next/internal/modules/site/contract"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
	sitestore "github.com/dujiao-next/internal/modules/site/infrastructure/gormstore"
	sitehttp "github.com/dujiao-next/internal/modules/site/transport/http"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/dujiao-next/internal/shared/money"
	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"github.com/shopspring/decimal"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

func setup(t *testing.T) (*gorm.DB, *sitestore.Store, *siteapp.Service) {
	t.Helper()
	db, err := gorm.Open(sqlite.Open(fmt.Sprintf("file:site-%d?mode=memory&cache=shared", time.Now().UnixNano())), &gorm.Config{})
	require.NoError(t, err)
	sql, err := db.DB()
	require.NoError(t, err)
	t.Cleanup(func() { _ = sql.Close() })
	require.NoError(t, db.AutoMigrate(&sitedomain.Site{}, &sitedomain.AdminScope{}, &sitedomain.Grant{}, &sitedomain.Visit{}, &userdomain.User{}, &admindomain.Admin{}, &orderdomain.Order{}, &orderdomain.OrderItem{}, &orderdomain.OrderRefundRecord{}, &paymentdomain.Payment{}, &productcatalogdomain.Item{}))
	s := sitestore.New(db)
	svc := siteapp.New(s, "gptpaynow.com", resellerapp.NewDomainResolver(nil, config.ResellerConfig{Enabled: false, TrustedForwardedHost: true}))
	return db, s, svc
}
func amt(s string) money.Amount { return money.FromDecimal(decimal.RequireFromString(s)) }
func filter(site uint) sitecontract.Filter {
	return sitecontract.Filter{SiteID: &site, From: time.Now().Add(-24 * time.Hour), To: time.Now().Add(24 * time.Hour), Page: 1, PageSize: 1}
}

type unavailableSiteDirectory struct{ sitecontract.Store }

func (unavailableSiteDirectory) FindDomain(string) (*sitedomain.Site, error) {
	return nil, fmt.Errorf("site directory unavailable")
}
func TestMainStorefrontAndPaymentHostsDoNotDependOnSiteDirectory(t *testing.T) {
	svc := siteapp.New(unavailableSiteDirectory{}, "gptpaynow.com", nil)
	for _, host := range []string{"gptpaynow.com", "www.gptpaynow.com", "pay.gptpaynow.com"} {
		tenant, err := svc.ResolveRequest(context.Background(), httptest.NewRequest("GET", "https://"+host+"/api/v1/public/config", nil))
		require.NoError(t, err)
		require.True(t, tenant.IsMain)
		require.Zero(t, tenant.SourceSiteID)
		require.Equal(t, host, tenant.Host)
	}
	_, err := svc.ResolveRequest(context.Background(), httptest.NewRequest("GET", "https://abc.gptpaynow.com/", nil))
	require.Error(t, err)
}
func TestSiteDomainsAndRevocation(t *testing.T) {
	db, store, svc := setup(t)
	for _, raw := range []string{"https://abc.gptpaynow.com", "*.gptpaynow.com", "abc.evil.com", "www.gptpaynow.com", "a.b.gptpaynow.com", "-abc.gptpaynow.com"} {
		require.Error(t, svc.SaveSite(&sitedomain.Site{Name: "bad", Domain: raw, Enabled: true}))
	}
	a := sitedomain.Site{Name: "ABC", Domain: "ABC.GPTPAYNOW.COM.", Enabled: true}
	require.NoError(t, svc.SaveSite(&a))
	require.Equal(t, "abc.gptpaynow.com", a.Domain)
	req := httptest.NewRequest("GET", "https://abc.gptpaynow.com/", nil)
	req.Header.Set("X-Forwarded-Host", "other.gptpaynow.com")
	tenant, err := svc.ResolveRequest(context.Background(), req)
	require.NoError(t, err)
	require.Equal(t, a.ID, tenant.SourceSiteID)
	req.Host = "gptpaynow.com"
	req.Header.Set("X-Forwarded-Host", a.Domain)
	tenant, err = svc.ResolveRequest(context.Background(), req)
	require.NoError(t, err)
	require.Zero(t, tenant.SourceSiteID)
	require.Equal(t, "gptpaynow.com", tenant.Host)
	req.Host = "unknown.gptpaynow.com"
	tenant, err = svc.ResolveRequest(context.Background(), req)
	require.NoError(t, err)
	require.True(t, tenant.Unavailable)
	a.Enabled = false
	require.NoError(t, svc.SaveSite(&a))
	req.Host = a.Domain
	tenant, err = svc.ResolveRequest(context.Background(), req)
	require.NoError(t, err)
	require.True(t, tenant.Unavailable)
	require.Error(t, svc.SaveSite(&sitedomain.Site{ID: a.ID, Name: "reassign", Domain: "xyz.gptpaynow.com", Enabled: true}))
	admin := admindomain.Admin{Username: "scoped", PasswordHash: "x"}
	require.NoError(t, db.Create(&admin).Error)
	require.NoError(t, svc.SetGrants(admin.ID, []sitedomain.Grant{{SiteID: a.ID, Orders: true}}))
	scope, err := store.GetScope(admin.ID)
	require.NoError(t, err)
	require.True(t, scope.Restricted)
	require.True(t, scope.Allows(a.ID, "orders"))
	require.False(t, scope.Allows(a.ID, "users"))
	require.NoError(t, svc.SetGrants(admin.ID, nil))
	scope, err = store.GetScope(admin.ID)
	require.NoError(t, err)
	require.True(t, scope.Restricted)
	require.Empty(t, scope.Grants)
	disabled := sitedomain.Site{Name: "Disabled", Domain: "disabled.gptpaynow.com", Enabled: false}
	require.NoError(t, svc.SaveSite(&disabled))
	loaded, err := store.FindDomain(disabled.Domain)
	require.NoError(t, err)
	require.False(t, loaded.Enabled)
	second := admindomain.Admin{Username: "second-scoped", PasswordHash: "x"}
	require.NoError(t, db.Create(&second).Error)
	require.NoError(t, svc.SetGrants(second.ID, []sitedomain.Grant{{SiteID: a.ID, Users: true}, {SiteID: disabled.ID, Visits: true}}))
	secondScope, err := store.GetScope(second.ID)
	require.NoError(t, err)
	require.True(t, secondScope.Allows(a.ID, "users"))
	require.True(t, secondScope.Allows(disabled.ID, "visits"))
	require.False(t, secondScope.Allows(a.ID, "orders"))
	firstScope, err := store.GetScope(admin.ID)
	require.NoError(t, err)
	require.Empty(t, firstScope.Grants)
}

func TestAddingSourceColumnsPreservesHistoricalRows(t *testing.T) {
	db, _, _ := setup(t)
	require.NoError(t, db.Exec("CREATE TABLE historical_users (id INTEGER PRIMARY KEY, email TEXT)").Error)
	require.NoError(t, db.Exec("INSERT INTO historical_users (id,email) VALUES (1,'historic@example.test')").Error)
	type historicalUser struct {
		ID                 uint `gorm:"primarykey"`
		Email              string
		RegistrationSiteID uint   `gorm:"not null;default:0;index"`
		RegistrationDomain string `gorm:"not null;default:''"`
	}
	require.NoError(t, db.Table("historical_users").AutoMigrate(&historicalUser{}))
	var row historicalUser
	require.NoError(t, db.Table("historical_users").First(&row, 1).Error)
	require.Equal(t, "historic@example.test", row.Email)
	require.Zero(t, row.RegistrationSiteID)
	require.Empty(t, row.RegistrationDomain)
}
func seed(t *testing.T, db *gorm.DB) {
	t.Helper()
	now := time.Now()
	u := userdomain.User{ID: 10, Email: "abc@example.test", PasswordHash: "secret", RegistrationSiteID: 1, RegistrationDomain: "abc.gptpaynow.com", AdminNote: "private-other-note"}
	require.NoError(t, db.Create(&u).Error)
	v := userdomain.User{ID: 11, Email: "xyz@example.test", PasswordHash: "secret", RegistrationSiteID: 2}
	require.NoError(t, db.Create(&v).Error)
	orders := []orderdomain.Order{
		{ID: 1, OrderNo: "ABC", UserID: 11, SourceSiteID: 1, SourceDomain: "abc.gptpaynow.com", Status: constants.OrderStatusPartiallyRefunded, Currency: "CNY", TotalAmount: amt("103"), RefundedAmount: amt("20.60"), InvoiceTaxAmount: amt("3"), CreatedAt: now},
		{ID: 2, OrderNo: "ABC-1", ParentID: ptr(1), SourceSiteID: 1, Status: constants.OrderStatusPartiallyRefunded, Currency: "CNY", TotalAmount: amt("103"), CreatedAt: now},
		{ID: 3, OrderNo: "XYZ", UserID: 10, SourceSiteID: 2, SourceDomain: "xyz.gptpaynow.com", Status: constants.OrderStatusCompleted, Currency: "CNY", TotalAmount: amt("900"), CreatedAt: now},
		{ID: 4, OrderNo: "USD", SourceSiteID: 1, Status: constants.OrderStatusPaid, Currency: "USD", TotalAmount: amt("10"), CreatedAt: now},
		{ID: 5, OrderNo: "UNPAID", SourceSiteID: 1, Status: constants.OrderStatusPendingPayment, Currency: "CNY", TotalAmount: amt("500"), CreatedAt: now},
		{ID: 6, OrderNo: "TAX", SourceSiteID: 1, Status: constants.OrderStatusPaid, Currency: "CNY", TotalAmount: amt("3"), Purpose: "invoice_tax", CreatedAt: now},
	}
	for i := range orders {
		require.NoError(t, db.Create(&orders[i]).Error)
	}
	for _, i := range []orderdomain.OrderItem{{OrderID: 2, ProductID: 1, TitleJSON: jsonmap.JSON{"zh-CN": "ABC product"}, Quantity: 1, CostPrice: amt("60")}, {OrderID: 3, ProductID: 1, TitleJSON: jsonmap.JSON{}, Quantity: 1, CostPrice: amt("500")}, {OrderID: 4, ProductID: 1, TitleJSON: jsonmap.JSON{}, Quantity: 1, CostPrice: amt("0")}} {
		require.NoError(t, db.Create(&i).Error)
	}
	require.NoError(t, db.Create(&productcatalogdomain.Item{ProductID: 1, SKUID: 0, CostPrice: amt("42")}).Error)
	p := paymentdomain.Payment{OrderID: 1, Status: constants.PaymentStatusSuccess, Currency: "CNY", Amount: amt("103"), FeeAmount: amt("2"), FeePolicy: constants.PaymentFeePolicyMerchantAbsorbed, ProviderType: "epay"}
	require.NoError(t, db.Create(&p).Error)
	r := orderdomain.OrderRefundRecord{OrderID: 2, Type: "test", Currency: "CNY", Amount: amt("20.60"), PaymentFeeRefundedAmount: amt("0.40")}
	require.NoError(t, db.Create(&r).Error)
}
func ptr(id uint) *uint { return &id }
func TestSiteDataAndDecimalProfitIsolation(t *testing.T) {
	db, store, _ := setup(t)
	seed(t, db)
	f := filter(1)
	users, n, err := store.ListUsers(f)
	require.NoError(t, err)
	require.EqualValues(t, 1, n)
	require.Equal(t, "abc@example.test", users[0].Email)
	orders, n, err := store.ListOrders(f)
	require.NoError(t, err)
	require.EqualValues(t, 3, n)
	require.Len(t, orders, 1)
	f.Page = 2
	orders, _, err = store.ListOrders(f)
	require.NoError(t, err)
	require.Len(t, orders, 1)
	require.Equal(t, uint(4), orders[0].ID)
	row, err := store.GetOrder(3, filter(1))
	require.NoError(t, err)
	require.Nil(t, row)
	row, err = store.GetOrder(1, filter(1))
	require.NoError(t, err)
	require.NotNil(t, row)
	require.Equal(t, "xyz@example.test", row.BuyerEmail)
	require.Len(t, row.Items, 1)
	raw, err := json.Marshal(row)
	require.NoError(t, err)
	require.NotContains(t, string(raw), "password")
	require.NotContains(t, string(raw), "admin_note")
	o, err := store.Overview(filter(1))
	require.NoError(t, err)
	require.EqualValues(t, 1, o.RegisteredUsers)
	require.Len(t, o.ByCurrency, 2)
	for _, r := range o.ByCurrency {
		if r.Currency == "CNY" {
			require.EqualValues(t, 2, r.Orders)
			require.EqualValues(t, 1, r.PaidOrders)
			require.Equal(t, "80.00", r.NetRevenue)
			require.Equal(t, "42.00", r.Cost)
			require.Equal(t, "1.60", r.PaymentFees)
			require.Equal(t, "36.40", r.Profit)
		} else {
			require.Equal(t, "-32.00", r.Profit)
			require.Zero(t, r.MissingCostOrders)
		}
	}
}
func TestScopedHTTPDeniesLegacyAndCrossSiteEvenWithWideRoles(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db, store, svc := setup(t)
	seed(t, db)
	require.NoError(t, store.SetGrants(8, []sitedomain.Grant{{AdminID: 8, SiteID: 1, Orders: true}}))
	policies, err := authz.NewService(db)
	require.NoError(t, err)
	require.NoError(t, policies.GrantRolePolicy("site-test-wide", "/admin/*", "*"))
	require.NoError(t, policies.SetAdminRoles(8, []string{"site-test-wide"}))
	r := gin.New()
	g := r.Group("/api/v1/admin", func(c *gin.Context) {
		c.Set("admin_id", uint(8))
		c.Set("admin_is_super", c.GetHeader("Test-Super") == "1")
	}, middleware.SiteAdminMiddleware(svc), middleware.AdminRBACMiddleware(policies))
	sitehttp.RegisterRoutes(g, sitehttp.New(svc))
	g.GET("/users", func(c *gin.Context) { c.String(200, "GLOBAL LEAK") })
	g.GET("/orders/:id", func(c *gin.Context) { c.String(200, "GLOBAL LEAK") })
	for _, p := range []string{"/users", "/orders/3", "/site-console/users?site_id=1", "/site-console/orders?site_id=2", "/site-console/orders", "/sites", "/site-console/orders?site_id=-1"} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", "/api/v1/admin"+p, nil))
		require.NotEqual(t, 200, w.Code, p)
		require.NotContains(t, w.Body.String(), "GLOBAL LEAK")
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/api/v1/admin/site-console/orders?site_id=1", nil))
	require.Equal(t, 200, w.Code)
	require.NotContains(t, w.Body.String(), "XYZ")
	w = httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/api/v1/admin/site-console/orders/3?site_id=1", nil))
	require.Equal(t, 404, w.Code)
	require.NoError(t, store.SetGrants(8, nil))
	w = httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/api/v1/admin/site-console/orders?site_id=1", nil))
	require.Equal(t, 403, w.Code)
	req := httptest.NewRequest("GET", "/api/v1/admin/site-console/orders", nil)
	req.Header.Set("Test-Super", "1")
	w = httptest.NewRecorder()
	r.ServeHTTP(w, req)
	require.Equal(t, 200, w.Code)
	require.Contains(t, w.Body.String(), "XYZ")
}

func TestIndividualAdministratorMenusOnSameSiteCanBeConfiguredAndRevokedIndependently(t *testing.T) {
	gin.SetMode(gin.TestMode)
	db, store, svc := setup(t)
	seed(t, db)
	site := sitedomain.Site{ID: 1, Name: "ABC", Domain: "abc.gptpaynow.com", Enabled: true}
	require.NoError(t, db.Create(&site).Error)
	for _, admin := range []admindomain.Admin{{ID: 8, Username: "order-support", PasswordHash: "hash"}, {ID: 9, Username: "finance-reader", PasswordHash: "hash"}} {
		require.NoError(t, db.Create(&admin).Error)
	}
	policies, err := authz.NewService(db)
	require.NoError(t, err) // No role membership is required for personal grants.
	r := gin.New()
	g := r.Group("/api/v1/admin", func(c *gin.Context) {
		id := uint(8)
		if c.GetHeader("Test-Admin") == "9" {
			id = 9
		}
		c.Set("admin_id", id)
		c.Set("admin_is_super", c.GetHeader("Test-Super") == "1")
	}, middleware.SiteAdminMiddleware(svc), middleware.AdminRBACMiddleware(policies))
	sitehttp.RegisterRoutes(g, sitehttp.New(svc))
	request := func(method, path, body, admin string, super bool) *httptest.ResponseRecorder {
		req := httptest.NewRequest(method, "/api/v1/admin"+path, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Test-Admin", admin)
		if super {
			req.Header.Set("Test-Super", "1")
		}
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)
		return w
	}
	w := request("PUT", "/sites/admins/8/grants", `{"grants":[{"site_id":1,"orders":true}]}`, "", true)
	require.Equal(t, 200, w.Code)
	w = request("PUT", "/sites/admins/9/grants", `{"grants":[{"site_id":1,"overview":true,"users":true}]}`, "", true)
	require.Equal(t, 200, w.Code)
	for _, check := range []struct {
		admin, menu string
		status      int
	}{{"8", "orders", 200}, {"8", "users", 403}, {"8", "overview", 403}, {"9", "users", 200}, {"9", "overview", 200}, {"9", "orders", 403}} {
		w = request("GET", "/site-console/"+check.menu+"?site_id=1", "", check.admin, false)
		require.Equal(t, check.status, w.Code, "admin %s menu %s", check.admin, check.menu)
	}
	w = request("PUT", "/sites/admins/9/grants", `{"grants":[{"site_id":1,"orders":true}]}`, "8", false)
	require.Equal(t, 403, w.Code)
	w = request("PUT", "/sites/admins/8/grants", `{"grants":[]}`, "", true)
	require.Equal(t, 200, w.Code)
	w = request("GET", "/site-console/orders?site_id=1", "", "8", false)
	require.Equal(t, 403, w.Code)
	w = request("GET", "/site-console/users?site_id=1", "", "9", false)
	require.Equal(t, 200, w.Code)
	scope, err := store.GetScope(9)
	require.NoError(t, err)
	require.True(t, scope.Allows(1, "overview"))
	require.False(t, scope.Allows(1, "orders"))
}
func TestBrowserVisitAndAuthenticatedAssociation(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_, store, svc := setup(t)
	site := sitedomain.Site{Name: "ABC", Domain: "abc.gptpaynow.com", Enabled: true}
	require.NoError(t, svc.SaveSite(&site))
	r := gin.New()
	r.Use(middleware.ResellerTenantMiddleware(svc), middleware.SiteVisitMiddleware(svc))
	r.GET("/api/v1/public/config", func(c *gin.Context) {
		if c.GetHeader("Test-User") == "1" {
			c.Set("user_id", uint(33))
		}
		c.JSON(200, gin.H{"ok": true})
	})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "https://abc.gptpaynow.com/api/v1/public/config", nil))
	require.Equal(t, 200, w.Code)
	require.NotEmpty(t, w.Result().Cookies())
	cookie := w.Result().Cookies()[0]
	req := httptest.NewRequest("GET", "https://abc.gptpaynow.com/api/v1/public/config", nil)
	req.AddCookie(cookie)
	req.Header.Set("Test-User", "1")
	r.ServeHTTP(httptest.NewRecorder(), req)
	req = httptest.NewRequest("GET", "https://abc.gptpaynow.com/api/v1/public/config", nil)
	req.AddCookie(cookie)
	r.ServeHTTP(httptest.NewRecorder(), req)
	visits, n, err := store.ListVisits(filter(site.ID))
	require.NoError(t, err)
	require.EqualValues(t, 1, n)
	require.Equal(t, uint(33), visits[0].UserID)
	overview, err := store.Overview(filter(site.ID))
	require.NoError(t, err)
	require.EqualValues(t, 1, overview.BrowserVisits)
	bad := httptest.NewRequest("POST", "https://unknown.gptpaynow.com/api/v1/orders", bytes.NewBufferString(`{"source_site_id":1}`))
	w = httptest.NewRecorder()
	r.ServeHTTP(w, bad)
	require.NotEqual(t, http.StatusOK, w.Code)
	_, err = svc.ResolveRequest(context.Background(), httptest.NewRequest("GET", "https://abc.gptpaynow.com", nil))
	require.NoError(t, err)
	require.False(t, strings.Contains(cookie.Value, "abc"))
}

func TestListVisitsIncludesAssociatedUserEmail(t *testing.T) {
	db, store, svc := setup(t)
	site := sitedomain.Site{Name: "ABC", Domain: "abc.gptpaynow.com", Enabled: true}
	require.NoError(t, svc.SaveSite(&site))
	user := userdomain.User{Email: "visitor@example.com", DisplayName: "Visitor", RegistrationDomain: site.Domain, RegistrationSiteID: site.ID}
	require.NoError(t, db.Create(&user).Error)
	now := time.Now()
	require.NoError(t, store.RecordVisit(sitedomain.Visit{SiteID: site.ID, Domain: site.Domain, Day: now.Format("2006-01-02"), VisitorHash: "email-test", UserID: user.ID, FirstSeenAt: now, LastSeenAt: now}))
	rows, total, err := store.ListVisits(filter(site.ID))
	require.NoError(t, err)
	require.EqualValues(t, 1, total)
	require.Len(t, rows, 1)
	require.Equal(t, user.Email, rows[0].UserEmail)
}

func TestRecordVisitMergesSameIPWithinFiveMinutes(t *testing.T) {
	_, store, svc := setup(t)
	site := sitedomain.Site{Name: "ABC", Domain: "abc.gptpaynow.com", Enabled: true}
	require.NoError(t, svc.SaveSite(&site))
	now := time.Now()
	base := sitedomain.Visit{SiteID: site.ID, Domain: site.Domain, Day: now.Format("2006-01-02"), VisitorHash: "ip-bucket-1", ClientIP: "203.0.113.10", Region: "中国 · 北京", FirstSeenAt: now, LastSeenAt: now}
	require.NoError(t, store.RecordVisit(base))
	updated := base
	updated.VisitorHash = "ip-bucket-2"
	updated.LastSeenAt = now.Add(2 * time.Minute)
	require.NoError(t, store.RecordVisit(updated))
	rows, total, err := store.ListVisits(filter(site.ID))
	require.NoError(t, err)
	require.EqualValues(t, 1, total)
	require.Len(t, rows, 1)
	require.Equal(t, updated.LastSeenAt.Unix(), rows[0].LastSeenAt.Unix())
	require.Equal(t, "203.0.113.10", rows[0].ClientIP)
	require.Equal(t, "中国 · 北京", rows[0].Region)

	later := base
	later.VisitorHash = "ip-bucket-3"
	later.FirstSeenAt = now.Add(70 * time.Minute)
	later.LastSeenAt = later.FirstSeenAt
	require.NoError(t, store.RecordVisit(later))
	_, total, err = store.ListVisits(filter(site.ID))
	require.NoError(t, err)
	require.EqualValues(t, 2, total)
}
