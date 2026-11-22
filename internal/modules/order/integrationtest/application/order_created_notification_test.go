package application_test

import (
	"github.com/dujiao-next/internal/constants"
	"github.com/dujiao-next/internal/modules/notification/contract"
	orderapp "github.com/dujiao-next/internal/modules/order/application"
	"testing"
)

type orderCreatedCollector struct{ events []contract.EnqueueInput }

func (c *orderCreatedCollector) Enqueue(input contract.EnqueueInput) error {
	c.events = append(c.events, input)
	return nil
}

func TestOrderCreatedNotificationAfterCommitOnly(t *testing.T) {
	f := newCouponLimitRaceFixture(t, "created_notification", 10, 0)
	svc := f.service(f.couponRepo, f.usageRepo)
	collector := &orderCreatedCollector{}
	svc.SetNotificationService(collector)
	order, err := svc.CreateOrder(f.input(f.users[0].ID))
	if err != nil {
		t.Fatal(err)
	}
	if len(collector.events) != 1 || collector.events[0].BizID != order.ID || collector.events[0].EventType != constants.NotificationEventOrderCreated {
		t.Fatalf("unexpected events: %#v", collector.events)
	}
	bad := f.input(f.users[0].ID)
	bad.Items[0].Quantity = 0
	if _, err := svc.CreateOrder(bad); err == nil {
		t.Fatal("expected invalid order")
	}
	if len(collector.events) != 1 {
		t.Fatal("failed order produced a notification")
	}
}

func TestGuestCreatedNotificationContainsOnlyPublicOrderFacts(t *testing.T) {
	f := newCouponLimitRaceFixture(t, "guest_created_notification", 10, 0)
	if err := f.db.Model(&f.product).Update("purchase_type", constants.ProductPurchaseGuest).Error; err != nil {
		t.Fatal(err)
	}
	svc := f.service(f.couponRepo, f.usageRepo)
	collector := &orderCreatedCollector{}
	svc.SetNotificationService(collector)
	order, err := svc.CreateGuestOrder(orderapp.CreateGuestOrderInput{Email: "guest-notify@example.com", OrderPassword: "private-order-password", Locale: "zh-CN", Items: f.input(0).Items})
	if err != nil {
		t.Fatal(err)
	}
	if len(collector.events) != 1 || collector.events[0].BizID != order.ID || len(collector.events[0].Data) != 5 {
		t.Fatal("unexpected guest notification")
	}
}
