package ginutil

import "github.com/gin-gonic/gin"

// PaymentContextAllowsOrder limits a main-site payment session to the single
// order that created it. Empty context means normal authenticated behavior.
func PaymentContextAllowsOrder(c *gin.Context, orderNo string) bool {
	if c == nil {
		return false
	}
	expected, ok := c.Get("payment_context_order_no")
	if !ok {
		return true
	}
	value, ok := expected.(string)
	return ok && value != "" && value == orderNo
}
