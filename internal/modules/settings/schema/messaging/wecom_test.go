package settingsmessaging

import (
	"encoding/json"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"strings"
	"testing"
)

const sampleHook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=01234567-89ab-cdef-0123-456789abcdef"

func TestWeComWebhookValidation(t *testing.T) {
	if err := ValidateWeComWebhook(sampleHook); err != nil {
		t.Fatal(err)
	}
	for _, raw := range []string{"", "http://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0123456789012345", strings.Replace(sampleHook, "qyapi.weixin.qq.com", "evil.example", 1), sampleHook + "&key=other", sampleHook + "&extra=1", sampleHook + "#fragment", strings.Replace(sampleHook, ".com/", ".com:443/", 1), strings.Replace(sampleHook, "https://", "https://user@", 1), strings.Replace(sampleHook, "/send?", "/upload_media?", 1)} {
		if err := ValidateWeComWebhook(raw); err == nil {
			t.Errorf("accepted invalid hook")
		} else if strings.Contains(err.Error(), "01234567") {
			t.Fatal("secret in error")
		}
	}
}

func TestWeComPatchRoundTripMaskAndClear(t *testing.T) {
	setting := NotificationCenterDefaultSetting()
	on, blank, hook := true, "", sampleHook
	next, err := ApplyNotificationCenterSettingPatch(setting, NotificationCenterSettingPatch{Channels: &NotificationChannelsPatch{WeCom: &WeComNotificationPatch{Enabled: &on, Webhook: &hook}}})
	if err != nil {
		t.Fatal(err)
	}
	next = DecodeNotificationCenterSetting(jsonmap.JSON(NotificationCenterSettingToMap(next)), setting)
	next, err = ApplyNotificationCenterSettingPatch(next, NotificationCenterSettingPatch{Channels: &NotificationChannelsPatch{WeCom: &WeComNotificationPatch{Webhook: &blank}}})
	if err != nil || next.Channels.WeCom.Webhook != hook || !next.Channels.WeCom.Enabled {
		t.Fatal("roundtrip/blank lost config", err)
	}
	masked, _ := json.Marshal(MaskNotificationCenterSettingForAdmin(next))
	if strings.Contains(string(masked), "01234567") || !strings.Contains(string(masked), `"has_webhook":true`) {
		t.Fatal("mask failed")
	}
	next, err = ApplyNotificationCenterSettingPatch(next, NotificationCenterSettingPatch{Channels: &NotificationChannelsPatch{WeCom: &WeComNotificationPatch{ClearWebhook: true}}})
	if err != nil || next.Channels.WeCom.Enabled || next.Channels.WeCom.Webhook != "" {
		t.Fatal("clear failed", err)
	}
}
