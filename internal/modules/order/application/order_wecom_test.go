package application

import (
	"encoding/json"
	"errors"
	"github.com/dujiao-next/internal/constants"
	"github.com/dujiao-next/internal/modules/notification/contract"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"strings"
	"testing"
)

type createdNotificationStub struct{ inputs []contract.EnqueueInput }

func (s *createdNotificationStub) Enqueue(in contract.EnqueueInput) error {
	s.inputs = append(s.inputs, in)
	return errors.New("queue unavailable")
}
func TestCreatedOrderNotificationOmitsSecretsAndChildren(t *testing.T) {
	stub := &createdNotificationStub{}
	s := &OrderService{notifications: stub}
	order := &orderdomain.Order{ID: 42, OrderNo: "TEST42", GuestPassword: "private-password", GuestEmail: "private-email", Items: []orderdomain.OrderItem{{ProductID: 8, Quantity: 2, TitleJSON: jsonmap.JSON{constants.LocaleZhCN: "ChatGPT Plus"}}}}
	s.notifyOrderCreated(order) // Queue failure is non-fatal.
	if len(stub.inputs) != 1 {
		t.Fatal("missing notification")
	}
	data, _ := json.Marshal(stub.inputs[0])
	if strings.Contains(string(data), "private") || !strings.Contains(string(data), "ChatGPT Plus") {
		t.Fatal("wrong payload")
	}
	parent := uint(42)
	order.ParentID = &parent
	s.notifyOrderCreated(order)
	s.notifyOrderCreated(nil)
	if len(stub.inputs) != 1 {
		t.Fatal("duplicate child event")
	}
}
