package invoicehttp

import "github.com/gin-gonic/gin"

func RegisterAdminRoutes(admin gin.IRoutes, h *Handler) {
	admin.GET("/invoices", h.ListAdmin)
	admin.POST("/invoices/:id/issued", h.MarkIssued)
}
