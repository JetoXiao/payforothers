package application

import (
	"context"
	"errors"
	"github.com/dujiao-next/internal/constants"
	"github.com/dujiao-next/internal/modules/notification/contract"
	settingsmessaging "github.com/dujiao-next/internal/modules/settings/schema/messaging"
	"github.com/dujiao-next/internal/queue"
	"strings"
	"testing"
)

type wecomStub struct {
	calls        int
	message, key string
	err          error
}

func (w *wecomStub) SendMessage(_ context.Context, _, key, message string) error {
	w.calls++
	w.message = message
	w.key = key
	return w.err
}
func TestWeComDispatchPrivacyAndToggle(t *testing.T) {
	cfg := NotificationSettingsForWeComTest()
	s := NewService(notificationSettingsStub{notification: cfg}, nil, nil, nil, nil, nil, nil)
	w := &wecomStub{}
	s.SetWeComSender(w)
	p := queue.NotificationDispatchPayload{EventType: constants.NotificationEventOrderCreated, BizType: constants.NotificationBizTypeOrder, BizID: 42, Data: map[string]interface{}{"order_no": "TEST42", "amount": "128.00", "currency": "CNY", "items_summary": "ChatGPT Plus × 1", "customer_email": "secret@email", "delivery_summary": "secret-code"}}
	if err := s.Dispatch(context.Background(), p); err != nil {
		t.Fatal(err)
	}
	if w.calls != 1 || w.key != "order_created:42" || strings.Contains(w.message, "secret") || !strings.Contains(w.message, "待支付") {
		t.Fatal("bad payload", w.message)
	}
	w.err = errors.New("retry")
	if s.Dispatch(context.Background(), p) == nil {
		t.Fatal("failure must reach queue")
	}
	cfg.Channels.WeCom.Enabled = false
	s.settingService = notificationSettingsStub{notification: cfg}
	if err := s.Dispatch(context.Background(), p); err != nil || w.calls != 2 {
		t.Fatal("disabled channel sent")
	}
	w.err = nil
	if err := s.SendTest(context.Background(), contract.TestSendInput{Channel: "wecom", Target: "untrusted-target"}); err != nil {
		t.Fatal(err)
	}
	if w.key != "" || !strings.Contains(w.message, "不是真实订单") {
		t.Fatal("test not labeled")
	}
}
func NotificationSettingsForWeComTest() settingsmessaging.NotificationCenterSetting {
	cfg := settingsmessaging.NotificationCenterDefaultSetting()
	cfg.Channels.WeCom = settingsmessaging.WeComNotificationSetting{Enabled: true, Webhook: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0123456789abcdef"}
	return cfg
}

type wecomQueueCapture struct {
	payload queue.NotificationDispatchPayload
	retries int
}

func (q *wecomQueueCapture) EnqueueNotificationDispatch(p queue.NotificationDispatchPayload, retries int) error {
	q.payload = p
	q.retries = retries
	return nil
}
func TestCreatedNotificationEnqueuesRetryableTask(t *testing.T) {
	q := &wecomQueueCapture{}
	s := NewService(notificationSettingsStub{notification: NotificationSettingsForWeComTest()}, nil, q, nil, nil, nil, nil)
	if err := s.Enqueue(contract.EnqueueInput{EventType: constants.NotificationEventOrderCreated, BizType: "order", BizID: 10}); err != nil {
		t.Fatal(err)
	}
	if q.payload.BizID != 10 || q.payload.EventType != constants.NotificationEventOrderCreated || q.retries != 15 {
		t.Fatal("incorrect queue task")
	}
}
