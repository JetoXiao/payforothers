package cache

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"strings"
	"time"
)

const paymentContextTTL = 10 * time.Minute

// PaymentContext is a short-lived, order-scoped bridge from a subdomain to the
// main payment UI. Guest credentials never appear in the URL; they remain in
// Redis until this context expires.
type PaymentContext struct {
	OrderNo      string `json:"order_no"`
	UserID       uint   `json:"user_id,omitempty"`
	GuestEmail   string `json:"guest_email,omitempty"`
	GuestSecret  string `json:"guest_secret,omitempty"`
	SourceSiteID uint   `json:"source_site_id,omitempty"`
}

func CreatePaymentContext(ctx context.Context, value PaymentContext) (string, error) {
	if strings.TrimSpace(value.OrderNo) == "" || (value.UserID == 0 && (strings.TrimSpace(value.GuestEmail) == "" || strings.TrimSpace(value.GuestSecret) == "")) {
		return "", errors.New("payment context identity is incomplete")
	}
	var raw [32]byte
	if _, err := rand.Read(raw[:]); err != nil {
		return "", err
	}
	token := base64.RawURLEncoding.EncodeToString(raw[:])
	if err := SetJSONRequired(ctx, "payment-context:"+token, value, paymentContextTTL); err != nil {
		return "", err
	}
	return token, nil
}

func GetPaymentContext(ctx context.Context, token string) (*PaymentContext, error) {
	token = strings.TrimSpace(token)
	if token == "" || len(token) > 128 {
		return nil, errors.New("payment context token is invalid")
	}
	var value PaymentContext
	hit, err := GetJSON(ctx, "payment-context:"+token, &value)
	if err != nil {
		return nil, err
	}
	if !hit {
		return nil, errors.New("payment context expired")
	}
	return &value, nil
}
