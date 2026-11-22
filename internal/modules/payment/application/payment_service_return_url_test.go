package application

import (
	"context"
	"net/url"
	"testing"
	"time"

	"github.com/dujiao-next/internal/constants"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	paymentdomain "github.com/dujiao-next/internal/modules/payment/domain"

	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/dujiao-next/internal/shared/money"
	"github.com/shopspring/decimal"
	"github.com/stretchr/testify/require"
)

func TestResolveTenantReturnURLMainTenantKeepsConfigFallback(t *testing.T) {
	ctx := resellercontract.WithTenantContext(context.Background(), resellercontract.MainTenantContext("main.example.com"))
	channel := &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{"return_url": "https://main.example.com/pay"}}

	if got := resolveTenantReturnURL(ctx, "https", channel); got != "" {
		t.Fatalf("main tenant want empty got %q", got)
	}
	if got := resolveTenantReturnURL(context.Background(), "https", channel); got != "" {
		t.Fatalf("no tenant want empty got %q", got)
	}
	//lint:ignore SA1012 This assertion deliberately verifies the nil-context fallback.
	if got := resolveTenantReturnURL(nil, "https", channel); got != "" {
		t.Fatalf("nil ctx want empty got %q", got)
	}
}

func TestResolveTenantReturnURLOperatorSiteUsesMainChannelConfiguration(t *testing.T) {
	tenant := resellercontract.MainTenantContext("abc.gptpaynow.com")
	tenant.SourceSiteID = 7
	ctx := resellercontract.WithTenantContext(context.Background(), tenant)
	channel := &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{"return_url": "https://gptpaynow.com/pay"}}
	if got := resolveTenantReturnURL(ctx, "https", channel); got != "" {
		t.Fatalf("operator site must leave the configured main return URL intact: %q", got)
	}
}

func TestOperatorSiteEpayUsesMainReturnAndNotifyAndPreservesOrderSource(t *testing.T) {
	svc, db := setupPaymentServiceWalletTest(t)
	channel := &paymentdomain.PaymentChannel{
		ProviderType: constants.PaymentProviderEpay, ChannelType: constants.PaymentChannelTypeAlipay,
		InteractionMode: constants.PaymentInteractionRedirect, IsActive: true,
		ConfigJSON: jsonmap.JSON{"gateway_url": "https://gateway.example.test", "epay_version": "v1", "merchant_id": "1001", "merchant_key": "test-key", "notify_url": "https://gptpaynow.com/api/v1/payments/callback", "return_url": "https://gptpaynow.com/pay"},
	}
	require.NoError(t, db.Create(channel).Error)
	for _, userID := range []uint{0, 42} {
		t.Run(map[bool]string{true: "guest", false: "member"}[userID == 0], func(t *testing.T) {
			now := time.Now()
			amount := money.FromDecimal(decimal.NewFromInt(20))
			order := &orderdomain.Order{OrderNo: buildGatewayOrderNo(), UserID: userID, SourceSiteID: 7, SourceDomain: "abc.gptpaynow.com", Status: constants.OrderStatusPendingPayment, Currency: "CNY", TotalAmount: amount, OnlinePaidAmount: amount, ExpiresAt: ptrTime(now.Add(time.Hour))}
			require.NoError(t, db.Create(order).Error)
			payment := &paymentdomain.Payment{OrderID: order.ID, ChannelID: channel.ID, ProviderType: channel.ProviderType, ChannelType: channel.ChannelType, InteractionMode: channel.InteractionMode, Amount: amount, Currency: "CNY", Status: constants.PaymentStatusInitiated}
			require.NoError(t, db.Create(payment).Error)
			tenant := resellercontract.MainTenantContext("abc.gptpaynow.com")
			tenant.SourceSiteID = 7
			require.NoError(t, svc.applyProviderPayment(CreatePaymentInput{Context: resellercontract.WithTenantContext(context.Background(), tenant), RequestScheme: "https"}, order, channel, payment))
			gateway, err := url.Parse(payment.PayURL)
			require.NoError(t, err)
			require.Equal(t, "gateway.example.test", gateway.Host)
			require.Equal(t, "https://gptpaynow.com/api/v1/payments/callback", gateway.Query().Get("notify_url"))
			returned, err := url.Parse(gateway.Query().Get("return_url"))
			require.NoError(t, err)
			require.Equal(t, "gptpaynow.com", returned.Host)
			require.Equal(t, "/pay", returned.Path)
			require.Equal(t, order.OrderNo, returned.Query().Get("order_no"))
			require.Equal(t, "1", returned.Query().Get("epay_return"))
			require.NotContains(t, payment.PayURL, "abc.gptpaynow.com")
			require.NoError(t, db.Save(payment).Error)
			// Callbacks resolve the stored order/payment, not the incoming host.
			_, err = svc.HandleCallback(PaymentCallbackInput{PaymentID: payment.ID, OrderNo: order.OrderNo, ChannelID: channel.ID, Status: constants.PaymentStatusSuccess, Amount: amount, Currency: "CNY", ProviderRef: "site-test"})
			require.NoError(t, err)
			var stored orderdomain.Order
			require.NoError(t, db.First(&stored, order.ID).Error)
			require.Equal(t, uint(7), stored.SourceSiteID)
			require.Equal(t, "abc.gptpaynow.com", stored.SourceDomain)
			require.Nil(t, stored.ResellerID)
			require.NotNil(t, stored.PaidAt)
		})
	}
}

func TestResolveTenantReturnURLResellerTenantUsesRequestHost(t *testing.T) {
	ctx := resellercontract.WithTenantContext(context.Background(), resellercontract.ResellerTenantContext("shop.example.com", 7, 3, "primary.example.com"))
	channel := &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{"return_url": "https://main.example.com/pay"}}

	if got := resolveTenantReturnURL(ctx, "https", channel); got != "https://shop.example.com/pay" {
		t.Fatalf("want https://shop.example.com/pay got %q", got)
	}
}

func TestResolveTenantReturnURLResellerTenantFallsBackToPrimaryDomain(t *testing.T) {
	ctx := resellercontract.WithTenantContext(context.Background(), resellercontract.ResellerTenantContext("", 7, 3, "primary.example.com"))

	if got := resolveTenantReturnURL(ctx, "https", nil); got != "https://primary.example.com/pay" {
		t.Fatalf("want https://primary.example.com/pay got %q", got)
	}
}

func TestResolveTenantReturnURLSchemeHandling(t *testing.T) {
	ctx := resellercontract.WithTenantContext(context.Background(), resellercontract.ResellerTenantContext("shop.example.com", 7, 3, "primary.example.com"))

	if got := resolveTenantReturnURL(ctx, "http", nil); got != "http://shop.example.com/pay" {
		t.Fatalf("http scheme want http://shop.example.com/pay got %q", got)
	}
	// 空值 / 非法值默认 https
	if got := resolveTenantReturnURL(ctx, "", nil); got != "https://shop.example.com/pay" {
		t.Fatalf("empty scheme want https got %q", got)
	}
	if got := resolveTenantReturnURL(ctx, "ftp", nil); got != "https://shop.example.com/pay" {
		t.Fatalf("invalid scheme want https got %q", got)
	}
}

func TestResolveTenantReturnURLUnavailableTenantKeepsConfigFallback(t *testing.T) {
	ctx := resellercontract.WithTenantContext(context.Background(), resellercontract.UnavailableTenantContext("gone.example.com", "disabled"))

	if got := resolveTenantReturnURL(ctx, "https", nil); got != "" {
		t.Fatalf("unavailable tenant want empty got %q", got)
	}
}

func TestTenantReturnPathReusesConfiguredPath(t *testing.T) {
	channel := &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{"return_url": "https://main.example.com/checkout/result?from=gateway"}}
	if got := tenantReturnPath(channel); got != "/checkout/result?from=gateway" {
		t.Fatalf("want /checkout/result?from=gateway got %q", got)
	}

	// stripe/dujiaopay 使用 success_url
	channel = &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{"success_url": "https://main.example.com/pay/success"}}
	if got := tenantReturnPath(channel); got != "/pay/success" {
		t.Fatalf("want /pay/success got %q", got)
	}

	// return_url 优先于 success_url
	channel = &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{
		"return_url":  "https://main.example.com/pay/return",
		"success_url": "https://main.example.com/pay/success",
	}}
	if got := tenantReturnPath(channel); got != "/pay/return" {
		t.Fatalf("want /pay/return got %q", got)
	}
}

func TestTenantReturnPathDefaults(t *testing.T) {
	if got := tenantReturnPath(nil); got != "/pay" {
		t.Fatalf("nil channel want /pay got %q", got)
	}
	if got := tenantReturnPath(&paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{}}); got != "/pay" {
		t.Fatalf("empty config want /pay got %q", got)
	}
	// 配置只有域名没有路径时也回落 /pay
	channel := &paymentdomain.PaymentChannel{ConfigJSON: jsonmap.JSON{"return_url": "https://main.example.com/"}}
	if got := tenantReturnPath(channel); got != "/pay" {
		t.Fatalf("root path want /pay got %q", got)
	}
}
