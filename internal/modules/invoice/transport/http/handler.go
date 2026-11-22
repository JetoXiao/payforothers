package invoicehttp

import (
	"strconv"
	"strings"

	invoicecontract "github.com/dujiao-next/internal/modules/invoice/contract"
	invoicedomain "github.com/dujiao-next/internal/modules/invoice/domain"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	"github.com/dujiao-next/internal/platform/http/ginutil"
	"github.com/dujiao-next/internal/platform/http/response"

	"github.com/gin-gonic/gin"
)

type ProfileInput struct {
	Name        string `json:"name" binding:"required"`
	Type        string `json:"type"`
	TaxpayerID  string `json:"taxpayer_id" binding:"required"`
	Address     string `json:"address"`
	Phone       string `json:"phone"`
	BankName    string `json:"bank_name"`
	BankAccount string `json:"bank_account"`
	Email       string `json:"email" binding:"required"`
	IsDefault   bool   `json:"is_default"`
}

type Handler struct {
	profiles invoicecontract.ProfileStore
	requests invoicecontract.RequestStore
	cancel   func(uint, uint) (*orderdomain.Order, error)
}

func NewHandler(profiles invoicecontract.ProfileStore, requests invoicecontract.RequestStore) *Handler {
	return &Handler{profiles: profiles, requests: requests}
}

func uid(c *gin.Context) (uint, bool)                                        { return ginutil.GetUserID(c) }
func (h *Handler) SetCancel(fn func(uint, uint) (*orderdomain.Order, error)) { h.cancel = fn }
func validateProfile(req ProfileInput) error {
	return invoicedomain.NormalizeProfile(toProfile(req, 1, 0), false)
}
func toProfile(req ProfileInput, userID uint, id uint) *invoicedomain.Profile {
	typ := strings.TrimSpace(req.Type)
	if typ == "" {
		typ = "ordinary"
	}
	return &invoicedomain.Profile{ID: id, UserID: userID, Name: strings.TrimSpace(req.Name), Type: typ, TaxpayerID: strings.TrimSpace(req.TaxpayerID), Address: strings.TrimSpace(req.Address), Phone: strings.TrimSpace(req.Phone), BankName: strings.TrimSpace(req.BankName), BankAccount: strings.TrimSpace(req.BankAccount), Email: strings.TrimSpace(req.Email), IsDefault: req.IsDefault}
}

func (h *Handler) ListProfiles(c *gin.Context) {
	id, ok := uid(c)
	if !ok {
		return
	}
	rows, err := h.profiles.ListByUser(id)
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.invoice_profile_fetch_failed", err)
		return
	}
	response.Success(c, rows)
}
func (h *Handler) CreateProfile(c *gin.Context) {
	id, ok := uid(c)
	if !ok {
		return
	}
	var req ProfileInput
	if err := c.ShouldBindJSON(&req); err != nil {
		ginutil.RespondBindError(c, err)
		return
	}
	if err := validateProfile(req); err != nil {
		ginutil.RespondError(c, response.CodeBadRequest, "error.invoice_profile_invalid", err)
		return
	}
	row := toProfile(req, id, 0)
	_ = invoicedomain.NormalizeProfile(row, false)
	if err := h.profiles.CreateProfile(row); err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.invoice_profile_save_failed", err)
		return
	}
	response.Success(c, row)
}
func (h *Handler) UpdateProfile(c *gin.Context) {
	id, ok := uid(c)
	if !ok {
		return
	}
	profileID, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	existing, err := h.profiles.GetByIDAndUser(uint(profileID), id)
	if err != nil || existing == nil {
		ginutil.RespondError(c, response.CodeNotFound, "error.invoice_profile_not_found", err)
		return
	}
	var req ProfileInput
	if err := c.ShouldBindJSON(&req); err != nil {
		ginutil.RespondBindError(c, err)
		return
	}
	if err := validateProfile(req); err != nil {
		ginutil.RespondError(c, response.CodeBadRequest, "error.invoice_profile_invalid", err)
		return
	}
	row := toProfile(req, id, existing.ID)
	_ = invoicedomain.NormalizeProfile(row, false)
	if err := h.profiles.Update(row); err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.invoice_profile_save_failed", err)
		return
	}
	response.Success(c, row)
}
func (h *Handler) DeleteProfile(c *gin.Context) {
	id, ok := uid(c)
	if !ok {
		return
	}
	profileID, _ := strconv.ParseUint(c.Param("id"), 10, 64)
	if err := h.profiles.Delete(uint(profileID), id); err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.invoice_profile_delete_failed", err)
		return
	}
	response.Success(c, gin.H{"deleted": true})
}
func (h *Handler) ListRequests(c *gin.Context) {
	id, ok := uid(c)
	if !ok {
		return
	}
	page, size := ginutil.ParsePagination(c)
	rows, total, err := h.requests.ListByUser(id, page, size)
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.invoice_request_fetch_failed", err)
		return
	}
	response.SuccessWithPage(c, rows, response.BuildPagination(page, size, total))
}

func RegisterUserRoutes(user gin.IRoutes, h *Handler) {
	user.GET("/me/invoice-profiles", h.ListProfiles)
	user.POST("/me/invoice-profiles", h.CreateProfile)
	user.PUT("/me/invoice-profiles/:id", h.UpdateProfile)
	user.DELETE("/me/invoice-profiles/:id", h.DeleteProfile)
	user.GET("/me/invoice-requests", h.ListRequests)
	user.POST("/me/invoice-requests/preview", h.PreviewRequest)
	user.POST("/me/invoice-requests", h.ApplyRequest)
	user.POST("/me/invoice-requests/:id/cancel", h.CancelRequest)
}
