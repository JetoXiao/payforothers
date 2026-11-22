package cataloghttp

import (
	"github.com/dujiao-next/internal/modules/productcatalog/contract"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/gin-gonic/gin"
	"github.com/shopspring/decimal"
	"strconv"
	"strings"
)

type Handler struct{ store contract.Store }

func New(s contract.Store) *Handler { return &Handler{store: s} }
func RegisterRoutes(r gin.IRoutes, h *Handler) {
	r.GET("/product-catalog", h.List)
	r.POST("/product-catalog/sync", h.Sync)
	r.PUT("/product-catalog/:id", h.Update)
}
func (h *Handler) List(c *gin.Context) {
	page, size := 1, 20
	if v, e := strconv.Atoi(c.Query("page")); e == nil && v > 0 {
		page = v
	}
	if v, e := strconv.Atoi(c.Query("page_size")); e == nil && v > 0 && v <= 100 {
		size = v
	}
	var active *bool
	if raw := c.Query("product_active"); raw != "" && raw != "all" {
		v := raw == "1" || strings.EqualFold(raw, "true")
		active = &v
	}
	rows, total, err := h.store.List(contract.Filter{Page: page, PageSize: size, Search: strings.TrimSpace(c.Query("search")), ProductActive: active})
	if err != nil {
		response.ErrorWithHTTPStatus(c, 500, 500, "Unable to load product catalog")
		return
	}
	out := make([]gin.H, 0, len(rows))
	for _, row := range rows {
		out = append(out, gin.H{"item": row, "effective_sale_price": row.EffectiveSalePrice(), "profit_amount": row.ProfitAmount(), "profit_rate": row.ProfitRate(), "inventory": row.Inventory()})
	}
	response.SuccessWithPage(c, out, response.BuildPagination(page, size, total))
}
func (h *Handler) Sync(c *gin.Context) {
	if !c.GetBool("admin_is_super") {
		response.ErrorWithHTTPStatus(c, 403, 403, "Only the super administrator can sync the product catalog")
		return
	}
	include := c.Query("include_inactive") == "1"
	var body struct {
		IncludeInactive bool `json:"include_inactive"`
	}
	if c.Request.Body != nil {
		_ = c.ShouldBindJSON(&body)
		include = include || body.IncludeInactive
	}
	n, err := h.store.Sync(include)
	if err != nil {
		response.ErrorWithHTTPStatus(c, 500, 500, "Unable to sync product catalog")
		return
	}
	response.Success(c, gin.H{"synced": n})
}
func (h *Handler) Update(c *gin.Context) {
	if !c.GetBool("admin_is_super") {
		response.ErrorWithHTTPStatus(c, 403, 403, "Only the super administrator can edit the product catalog")
		return
	}
	id, e := strconv.ParseUint(c.Param("id"), 10, 32)
	if e != nil || id == 0 {
		response.ErrorWithHTTPStatus(c, 400, 400, "Invalid catalog item")
		return
	}
	var req struct {
		CostPrice          *string `json:"cost_price"`
		SalePrice          *string `json:"sale_price"`
		FollowProductPrice *bool   `json:"follow_product_price"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.ErrorWithHTTPStatus(c, 400, 400, "Invalid catalog item")
		return
	}
	fields := map[string]interface{}{}
	if req.CostPrice != nil {
		if value, err := decimal.NewFromString(strings.TrimSpace(*req.CostPrice)); err != nil || value.IsNegative() {
			response.ErrorWithHTTPStatus(c, 400, 400, "Invalid cost price")
			return
		}
		fields["cost_price"] = *req.CostPrice
	}
	if req.SalePrice != nil {
		if value, err := decimal.NewFromString(strings.TrimSpace(*req.SalePrice)); err != nil || value.IsNegative() {
			response.ErrorWithHTTPStatus(c, 400, 400, "Invalid sale price")
			return
		}
		fields["sale_price"] = *req.SalePrice
	}
	if req.FollowProductPrice != nil {
		fields["follow_product_price"] = *req.FollowProductPrice
	}
	if len(fields) == 0 {
		response.ErrorWithHTTPStatus(c, 400, 400, "No fields to update")
		return
	}
	item, err := h.store.Update(uint(id), fields)
	if err != nil {
		response.ErrorWithHTTPStatus(c, 400, 400, "Unable to update catalog item")
		return
	}
	response.Success(c, item)
}
