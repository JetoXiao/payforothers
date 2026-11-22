package cache

import (
	"context"
	"testing"
)

func TestPaymentContextRejectsIncompleteIdentityWithoutRedis(t *testing.T) {
	_, err := CreatePaymentContext(context.Background(), PaymentContext{OrderNo: "ORDER-1", SourceSiteID: 7})
	if err == nil {
		t.Fatal("guest or member identity must be present")
	}
	_, err = CreatePaymentContext(context.Background(), PaymentContext{GuestEmail: "guest@example.test", GuestSecret: "password", SourceSiteID: 7})
	if err == nil {
		t.Fatal("Redis-backed context must fail closed when Redis is unavailable")
	}
}
