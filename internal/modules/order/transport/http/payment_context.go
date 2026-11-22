package orderhttp

import (
	"github.com/dujiao-next/internal/cache"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	orderpresenter "github.com/dujiao-next/internal/modules/order/transport/presenter"
	reseller "github.com/dujiao-next/internal/modules/reseller/contract"
	"github.com/gin-gonic/gin"
)

func attachPaymentContext(c *gin.Context, order *orderdomain.Order, guestSecret string) string {
	if c == nil || order == nil || order.Status != "pending_payment" {
		return ""
	}
	if existing, ok := c.Get("payment_context_token"); ok {
		if token, valid := existing.(string); valid && token != "" {
			return token
		}
	}
	tenant, ok := reseller.TenantFromContext(c.Request.Context())
	if !ok || tenant.SourceSiteID == 0 {
		return ""
	}
	token, err := cache.CreatePaymentContext(c.Request.Context(), cache.PaymentContext{OrderNo: order.OrderNo, UserID: order.UserID, GuestEmail: order.GuestEmail, GuestSecret: guestSecret, SourceSiteID: tenant.SourceSiteID})
	if err != nil {
		return ""
	}
	return token
}
func attachSummaryContexts(c *gin.Context, orders []orderdomain.Order, summaries []orderpresenter.OrderSummary, guestSecret string) {
	for i := range summaries {
		if i < len(orders) {
			summaries[i].PaymentContext = attachPaymentContext(c, &orders[i], guestSecret)
		}
	}
}
