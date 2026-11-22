package application

import (
	"context"
	"fmt"
	"strings"
	"time"
	"unicode"

	"github.com/dujiao-next/internal/constants"
	"github.com/dujiao-next/internal/modules/notification/contract"
	settingsmessaging "github.com/dujiao-next/internal/modules/settings/schema/messaging"
	"github.com/dujiao-next/internal/queue"
)

func (s *Service) dispatchWeComOrder(ctx context.Context, setting settingsmessaging.NotificationCenterSetting, payload queue.NotificationDispatchPayload) error {
	if !setting.Channels.WeCom.Enabled {
		return nil
	}
	if payload.BizType != constants.NotificationBizTypeOrder || payload.BizID == 0 {
		return contract.ErrEventInvalid
	}
	// Explicit allowlist: never forward delivery content, form data or customer credentials.
	values := map[string]interface{}{}
	for _, key := range []string{"order_no", "amount", "currency", "items_summary", "created_at"} {
		if val, ok := payload.Data[key].(string); ok {
			values[key] = val
		}
	}
	field := func(key string) string {
		v, _ := values[key].(string)
		return strings.Map(func(r rune) rune {
			if unicode.IsControl(r) && r != '\n' {
				return -1
			}
			return r
		}, v)
	}
	title := "GptPayNow · 新订单"
	body := fmt.Sprintf("订单号：%s\n订单金额：%s %s\n创建状态：待支付（不代表已收款）\n下单时间：%s\n商品：\n%s\n请登录管理后台核实当前支付及交付状态。", field("order_no"), field("amount"), field("currency"), field("created_at"), field("items_summary"))
	return s.sendWeCom(ctx, setting, payload.BizID, title, body, values, false)
}

func (s *Service) sendWeComTest(ctx context.Context, setting settingsmessaging.NotificationCenterSetting) error {
	return s.sendWeCom(ctx, setting, 0, "GptPayNow · 企业微信推送测试", "这是一条测试消息，不是真实订单，也不代表已付款。\n新订单通知连接正常。正式通知包含订单号、商品、金额及创建状态，请以管理后台实际状态为准。", nil, true)
}

func (s *Service) sendWeCom(ctx context.Context, setting settingsmessaging.NotificationCenterSetting, orderID uint, title, body string, values map[string]interface{}, test bool) error {
	if s.wecomSender == nil || setting.Channels.WeCom.Webhook == "" {
		return contract.ErrConfigInvalid
	}
	key := ""
	if !test {
		key = fmt.Sprintf("order_created:%d", orderID)
	}
	sendCtx, cancel := context.WithTimeout(ctx, 12*time.Second)
	defer cancel()
	err := s.wecomSender.SendMessage(sendCtx, setting.Channels.WeCom.Webhook, key, title+"\n"+body)
	s.recordSendAttempt(notificationSendAttempt{eventType: constants.NotificationEventOrderCreated, bizType: constants.NotificationBizTypeOrder, bizID: orderID, channel: constants.NotificationChannelWeCom, recipient: "configured-group", locale: constants.LocaleZhCN, title: title, body: body, variables: values, isTest: test, sendErr: err})
	return err
}
