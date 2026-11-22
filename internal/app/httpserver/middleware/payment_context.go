package middleware

import (
	"strings"

	"github.com/dujiao-next/internal/cache"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/gin-gonic/gin"
)

const paymentContextHeader = "X-Payment-Context"

func PaymentContextMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		token := strings.TrimSpace(c.GetHeader(paymentContextHeader))
		if token == "" {
			c.Next()
			return
		}
		value, err := cache.GetPaymentContext(c.Request.Context(), token)
		if err != nil || value == nil {
			response.ErrorWithHTTPStatus(c, 401, response.CodeUnauthorized, "Payment session expired")
			return
		}
		c.Set("payment_context_order_no", value.OrderNo)
		c.Set("payment_context_token", token)
		c.Set("payment_context_user_id", value.UserID)
		c.Set("payment_context_guest_email", value.GuestEmail)
		c.Set("payment_context_guest_secret", value.GuestSecret)
		c.Set("payment_context_site_id", value.SourceSiteID)
		c.Next()
	}
}

func PaymentContextGuestGuard() gin.HandlerFunc {
	return func(c *gin.Context) {
		if _, exists := c.Get("payment_context_order_no"); !exists {
			c.Next()
			return
		}
		path := c.FullPath()
		allowed := (strings.Contains(path, "/guest/orders/") && !strings.HasSuffix(path, "/fulfillment/download")) || strings.HasSuffix(path, "/guest/payments/latest") || strings.HasSuffix(path, "/guest/payments") || strings.Contains(path, "/guest/payments/")
		if !allowed {
			response.ErrorWithHTTPStatus(c, 403, response.CodeForbidden, "Payment session cannot access this resource")
			return
		}
		c.Next()
	}
}

func paymentContextAllowsOrder(c *gin.Context, orderNo string) bool {
	if expected, ok := c.Get("payment_context_order_no"); ok {
		return strings.TrimSpace(expected.(string)) == strings.TrimSpace(orderNo)
	}
	return true
}
