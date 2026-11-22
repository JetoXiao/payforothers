package sitehttp

import (
	"strconv"
	"strings"
	"time"

	"github.com/dujiao-next/internal/logger"
	auditlogapp "github.com/dujiao-next/internal/modules/auditlog/application"
	siteapp "github.com/dujiao-next/internal/modules/site/application"
	sitecontract "github.com/dujiao-next/internal/modules/site/contract"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/gin-gonic/gin"
)

type AuditRecorder interface {
	Record(auditlogapp.AuthzRecord) error
}
type Handler struct {
	service *siteapp.Service
	audit   AuditRecorder
}

func New(s *siteapp.Service) *Handler                     { return &Handler{service: s} }
func (h *Handler) WithAudit(audit AuditRecorder) *Handler { h.audit = audit; return h }
func (h *Handler) record(c *gin.Context, action string, target *uint, detail jsonmap.JSON) {
	if h.audit == nil {
		return
	}
	if err := h.audit.Record(auditlogapp.AuthzRecord{OperatorAdminID: c.GetUint("admin_id"), OperatorUsername: c.GetString("username"), TargetAdminID: target, Action: action, Object: c.FullPath(), Method: c.Request.Method, RequestID: c.GetString("request_id"), Detail: detail}); err != nil {
		logger.Errorw("site_admin_audit_failed", "action", action, "error", err)
	}
}
func RegisterRoutes(r gin.IRoutes, h *Handler) {
	r.GET("/sites", h.Sites)
	r.POST("/sites", h.SaveSite)
	r.PUT("/sites/:id", h.SaveSite)
	r.POST("/sites/:id/certificate", h.RequestCertificate)
	r.GET("/sites/:id/certificate", h.Certificate)
	r.GET("/sites/admins/:id/grants", h.Grants)
	r.PUT("/sites/admins/:id/grants", h.SaveGrants)
	r.GET("/site-console/scope", h.Scope)
	r.GET("/site-console/overview", h.Overview)
	r.GET("/site-console/users", h.Users)
	r.GET("/site-console/orders", h.Orders)
	r.GET("/site-console/orders/:id", h.Order)
	r.GET("/site-console/visits", h.Visits)
}
func failure(c *gin.Context, status int, msg string) {
	response.ErrorWithHTTPStatus(c, status, status, msg)
}
func super(c *gin.Context) bool {
	if !c.GetBool("admin_is_super") {
		failure(c, 403, "Only the super administrator can manage sites and grants")
		return false
	}
	return true
}
func (h *Handler) Sites(c *gin.Context) {
	if !super(c) {
		return
	}
	rows, err := h.service.Store.ListSites()
	if err != nil {
		failure(c, 500, "Unable to load sites")
		return
	}
	for i := range rows {
		siteapp.DecorateCertificate(&rows[i])
	}
	response.Success(c, rows)
}
func (h *Handler) SaveSite(c *gin.Context) {
	if !super(c) {
		return
	}
	var row sitedomain.Site
	if err := c.ShouldBindJSON(&row); err != nil {
		failure(c, 400, "Invalid site")
		return
	}
	row.ID = 0
	if id := c.Param("id"); id != "" {
		n, err := strconv.ParseUint(id, 10, 32)
		if err != nil || n == 0 {
			failure(c, 400, "Invalid site id")
			return
		}
		row.ID = uint(n)
	}
	if err := h.service.SaveSite(&row); err != nil {
		failure(c, 400, "Site unavailable, domain already reserved, or invalid site")
		return
	}
	h.record(c, "site_save", nil, jsonmap.JSON{"site_id": row.ID, "domain": row.Domain, "name": row.Name, "enabled": row.Enabled})
	response.Success(c, row)
}

func (h *Handler) RequestCertificate(c *gin.Context) {
	if !super(c) {
		return
	}
	id, ok := parseID(c)
	if !ok {
		return
	}
	rows, err := h.service.Store.ListSites()
	if err != nil {
		failure(c, 500, "Unable to load site")
		return
	}
	var site *sitedomain.Site
	for i := range rows {
		if rows[i].ID == id {
			site = &rows[i]
			break
		}
	}
	if site == nil {
		failure(c, 404, "Site not found")
		return
	}
	if err := siteapp.RequestCertificate(site); err != nil {
		failure(c, 400, err.Error())
		return
	}
	siteapp.DecorateCertificate(site)
	h.record(c, "site_certificate_request", &id, jsonmap.JSON{"site_id": id, "domain": site.Domain})
	response.Success(c, site)
}

func (h *Handler) Certificate(c *gin.Context) {
	if !super(c) {
		return
	}
	id, ok := parseID(c)
	if !ok {
		return
	}
	rows, err := h.service.Store.ListSites()
	if err != nil {
		failure(c, 500, "Unable to load site")
		return
	}
	for _, site := range rows {
		if site.ID == id {
			status := siteapp.ReadCertificateStatus(id)
			response.Success(c, status)
			return
		}
	}
	failure(c, 404, "Site not found")
}
func (h *Handler) Grants(c *gin.Context) {
	if !super(c) {
		return
	}
	id, ok := parseID(c)
	if !ok {
		return
	}
	scope, err := h.service.Store.GetScope(id)
	if err != nil {
		failure(c, 500, "Unable to load grants")
		return
	}
	response.Success(c, scope)
}
func (h *Handler) SaveGrants(c *gin.Context) {
	if !super(c) {
		return
	}
	id, ok := parseID(c)
	if !ok {
		return
	}
	var req struct {
		Grants []sitedomain.Grant `json:"grants"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || len(req.Grants) > 100 {
		failure(c, 400, "Invalid grants")
		return
	}
	if err := h.service.SetGrants(id, req.Grants); err != nil {
		failure(c, 400, "Invalid administrator or site grant")
		return
	}
	h.record(c, "site_admin_grants_update", &id, jsonmap.JSON{"grants": req.Grants, "restricted": true})
	response.Success(c, gin.H{"restricted": true, "grants": req.Grants})
}
func parseID(c *gin.Context) (uint, bool) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil || id == 0 {
		failure(c, 400, "Invalid id")
		return 0, false
	}
	return uint(id), true
}
func (h *Handler) Scope(c *gin.Context) {
	scope, err := h.service.Store.GetScope(c.GetUint("admin_id"))
	if err != nil {
		failure(c, 500, "Unable to load scope")
		return
	}
	rows, err := h.service.Store.ListSites()
	if err != nil {
		failure(c, 500, "Unable to load sites")
		return
	}
	visible := []sitedomain.Site{}
	for _, row := range rows {
		if c.GetBool("admin_is_super") {
			siteapp.DecorateCertificate(&row)
			visible = append(visible, row)
			continue
		}
		for _, g := range scope.Grants {
			if g.SiteID == row.ID {
				siteapp.DecorateCertificate(&row)
				visible = append(visible, row)
				break
			}
		}
	}
	response.Success(c, gin.H{"restricted": scope.Restricted, "grants": scope.Grants, "sites": visible, "is_super": c.GetBool("admin_is_super"), "base_domain": h.service.BaseDomain})
}
func (h *Handler) filter(c *gin.Context, menu string) (sitecontract.Filter, bool) {
	f := sitecontract.Filter{Page: 1, PageSize: 20, Keyword: strings.TrimSpace(c.Query("keyword")), Status: strings.TrimSpace(c.Query("status"))}
	if raw, exists := c.GetQuery("site_id"); exists {
		v, err := strconv.ParseUint(raw, 10, 32)
		if err != nil {
			failure(c, 400, "Invalid site id")
			return f, false
		}
		id := uint(v)
		f.SiteID = &id
	}
	if !c.GetBool("admin_is_super") {
		scope, err := h.service.Store.GetScope(c.GetUint("admin_id"))
		if err != nil {
			failure(c, 500, "Unable to load scope")
			return f, false
		}
		if !scope.Restricted || f.SiteID == nil || !scope.Allows(*f.SiteID, menu) {
			failure(c, 403, "Site or menu not authorized")
			return f, false
		}
	}
	loc, _ := time.LoadLocation("Asia/Shanghai")
	if loc == nil {
		loc = time.FixedZone("Asia/Shanghai", 8*3600)
	}
	today := time.Now().In(loc)
	today = time.Date(today.Year(), today.Month(), today.Day(), 0, 0, 0, 0, loc)
	f.From = today.AddDate(0, 0, -29)
	f.To = today.AddDate(0, 0, 1)
	if raw := c.Query("from"); raw != "" {
		v, err := time.ParseInLocation("2006-01-02", raw, loc)
		if err != nil {
			failure(c, 400, "Invalid from date")
			return f, false
		}
		f.From = v
	}
	if raw := c.Query("to"); raw != "" {
		v, err := time.ParseInLocation("2006-01-02", raw, loc)
		if err != nil {
			failure(c, 400, "Invalid to date")
			return f, false
		}
		f.To = v.AddDate(0, 0, 1)
	}
	if !f.From.Before(f.To) || f.To.Sub(f.From) > 366*24*time.Hour {
		failure(c, 400, "Select a date range of at most 366 days")
		return f, false
	}
	if raw := c.Query("page"); raw != "" {
		v, e := strconv.Atoi(raw)
		if e != nil || v < 1 || v > 1000000 {
			failure(c, 400, "Invalid page")
			return f, false
		}
		f.Page = v
	}
	if raw := c.Query("page_size"); raw != "" {
		v, e := strconv.Atoi(raw)
		if e != nil || v < 1 || v > 100 {
			failure(c, 400, "Invalid page size")
			return f, false
		}
		f.PageSize = v
	}
	return f, true
}
func page(c *gin.Context, rows interface{}, n int64, f sitecontract.Filter, err error) {
	if err != nil {
		failure(c, 500, "Unable to load site data")
		return
	}
	response.SuccessWithPage(c, rows, response.BuildPagination(f.Page, f.PageSize, n))
}
func (h *Handler) Overview(c *gin.Context) {
	f, ok := h.filter(c, "overview")
	if !ok {
		return
	}
	row, err := h.service.Store.Overview(f)
	if err != nil {
		failure(c, 500, "Unable to load overview")
		return
	}
	response.Success(c, row)
}
func (h *Handler) Users(c *gin.Context) {
	f, ok := h.filter(c, "users")
	if !ok {
		return
	}
	rows, n, err := h.service.Store.ListUsers(f)
	page(c, rows, n, f, err)
}
func (h *Handler) Orders(c *gin.Context) {
	f, ok := h.filter(c, "orders")
	if !ok {
		return
	}
	rows, n, err := h.service.Store.ListOrders(f)
	page(c, rows, n, f, err)
}
func (h *Handler) Visits(c *gin.Context) {
	f, ok := h.filter(c, "visits")
	if !ok {
		return
	}
	rows, n, err := h.service.Store.ListVisits(f)
	page(c, rows, n, f, err)
}
func (h *Handler) Order(c *gin.Context) {
	f, ok := h.filter(c, "orders")
	if !ok {
		return
	}
	id, ok := parseID(c)
	if !ok {
		return
	}
	row, err := h.service.Store.GetOrder(id, f)
	if err != nil {
		failure(c, 500, "Unable to load order")
		return
	}
	if row == nil {
		failure(c, 404, "Order not found")
		return
	}
	response.Success(c, row)
}
