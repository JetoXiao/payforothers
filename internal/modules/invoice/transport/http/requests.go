package invoicehttp

import (
	"errors"
	d "github.com/dujiao-next/internal/modules/invoice/domain"
	"github.com/dujiao-next/internal/platform/http/ginutil"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/gin-gonic/gin"
	"strconv"
)

type RequestInput struct {
	ProfileID   uint     `json:"profile_id" binding:"required"`
	InvoiceType string   `json:"invoice_type" binding:"required"`
	OrderNos    []string `json:"order_nos" binding:"required"`
}

func fail(c *gin.Context, err error) {
	code := response.CodeInternal
	key := "error.internal_error"
	if errors.Is(err, d.ErrInvalid) || errors.Is(err, d.ErrConflict) || errors.Is(err, d.ErrUnavailable) || errors.Is(err, d.ErrNotFound) {
		code = response.CodeBadRequest
		key = "error.invoice_invalid"
	}
	ginutil.RespondError(c, code, key, nil)
}
func (h *Handler) apply(c *gin.Context, preview bool) {
	user, ok := uid(c)
	if !ok {
		return
	}
	var input RequestInput
	if err := c.ShouldBindJSON(&input); err != nil {
		ginutil.RespondBindError(c, err)
		return
	}
	r, err := h.requests.Apply(user, input.ProfileID, input.InvoiceType, input.OrderNos, preview)
	if err != nil {
		fail(c, err)
		return
	}
	response.Success(c, r)
}
func (h *Handler) ApplyRequest(c *gin.Context)   { h.apply(c, false) }
func (h *Handler) PreviewRequest(c *gin.Context) { h.apply(c, true) }
func (h *Handler) CancelRequest(c *gin.Context) {
	user, ok := uid(c)
	if !ok {
		return
	}
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		fail(c, d.ErrInvalid)
		return
	}
	r, err := h.requests.GetByIDAndUser(uint(id), user)
	if err != nil {
		fail(c, err)
		return
	}
	if r.Status != d.StatusPendingTaxPayment || r.PaymentOrderID == nil || h.cancel == nil {
		fail(c, d.ErrConflict)
		return
	}
	if _, err := h.cancel(*r.PaymentOrderID, user); err != nil {
		fail(c, d.ErrConflict)
		return
	}
	response.Success(c, gin.H{"canceled": true})
}
func (h *Handler) ListAdmin(c *gin.Context) {
	page, size := ginutil.ParsePagination(c)
	rows, total, err := h.requests.ListAdmin(page, size)
	if err != nil {
		fail(c, err)
		return
	}
	response.SuccessWithPage(c, rows, response.BuildPagination(page, size, total))
}
func (h *Handler) MarkIssued(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 32)
	if err != nil {
		fail(c, d.ErrInvalid)
		return
	}
	var input struct {
		InvoiceNumber string `json:"invoice_number"`
		Sent          bool   `json:"email_sent"`
	}
	if err := c.ShouldBindJSON(&input); err != nil || !input.Sent {
		fail(c, d.ErrInvalid)
		return
	}
	result, err := h.requests.MarkIssued(uint(id), c.GetUint("admin_id"), input.InvoiceNumber)
	if err != nil {
		fail(c, err)
		return
	}
	response.Success(c, result)
}
