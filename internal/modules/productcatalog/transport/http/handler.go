package cataloghttp

import (
	"encoding/json"
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
	r.DELETE("/product-catalog/:id", h.Delete)
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
		out = append(out, gin.H{
			"id": row.ID, "product_id": row.ProductID, "sku_id": row.SKUID,
			"product_slug": row.ProductSlug, "title": row.TitleJSON, "images": row.ImagesJSON,
			"sku_code": row.SKUCode, "spec_values": row.SpecValuesJSON,
			"product_active": row.ProductActive, "sku_active": row.SKUActive,
			"product_price": row.ProductPrice, "cost_price": row.CostPrice, "sale_price": row.SalePrice,
			"follow_product_price": row.FollowProductPrice,
			"manual_stock":         row.ManualStock, "manual_locked": row.ManualLocked, "manual_sold": row.ManualSold,
			"auto_stock": row.AutoStock, "effective_sale_price": row.EffectiveSalePrice(),
			"profit_amount": row.ProfitAmount(), "profit_rate": row.ProfitRate(), "inventory": row.Inventory(),
		})
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
		CostPrice          json.RawMessage `json:"cost_price"`
		SalePrice          json.RawMessage `json:"sale_price"`
		FollowProductPrice *bool           `json:"follow_product_price"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		response.ErrorWithHTTPStatus(c, 400, 400, "Invalid catalog item")
		return
	}
	fields := map[string]interface{}{}
	if len(req.CostPrice) > 0 && string(req.CostPrice) != "null" {
		valueText, err := catalogMoneyText(req.CostPrice)
		if err != nil {
			response.ErrorWithHTTPStatus(c, 400, 400, "Invalid cost price")
			return
		}
		if value, err := decimal.NewFromString(valueText); err != nil || value.IsNegative() {
			response.ErrorWithHTTPStatus(c, 400, 400, "Invalid cost price")
			return
		}
		fields["cost_price"] = valueText
	}
	if len(req.SalePrice) > 0 && string(req.SalePrice) != "null" {
		valueText, err := catalogMoneyText(req.SalePrice)
		if err != nil {
			response.ErrorWithHTTPStatus(c, 400, 400, "Invalid sale price")
			return
		}
		if value, err := decimal.NewFromString(valueText); err != nil || value.IsNegative() {
			response.ErrorWithHTTPStatus(c, 400, 400, "Invalid sale price")
			return
		}
		fields["sale_price"] = valueText
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

func (h *Handler) Delete(c *gin.Context) {
	if !c.GetBool("admin_is_super") {
		response.ErrorWithHTTPStatus(c, 403, 403, "Only the super administrator can delete product catalog items")
		return
	}
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil || id == 0 {
		response.ErrorWithHTTPStatus(c, 400, 400, "Invalid catalog item")
		return
	}
	if err := h.store.Delete(uint(id)); err != nil {
		response.ErrorWithHTTPStatus(c, 400, 400, "Unable to delete catalog item")
		return
	}
	response.Success(c, gin.H{"deleted": true})
}

func catalogMoneyText(raw json.RawMessage) (string, error) {
	var text string
	if len(raw) > 0 && raw[0] == '"' {
		if err := json.Unmarshal(raw, &text); err != nil {
			return "", err
		}
		return strings.TrimSpace(text), nil
	}
	var number json.Number
	if err := json.Unmarshal(raw, &number); err != nil {
		return "", err
	}
	return strings.TrimSpace(number.String()), nil
}
