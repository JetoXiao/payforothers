package settingshttp

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"

	"github.com/dujiao-next/internal/constants"
	settingsapp "github.com/dujiao-next/internal/modules/settings/application"
	settingsmessaging "github.com/dujiao-next/internal/modules/settings/schema/messaging"
	"github.com/dujiao-next/internal/shared/jsonmap"
)

type adminSettingsStub struct {
	updateCalls int
	value       jsonmap.JSON
}

func (s *adminSettingsStub) GetByKey(string) (jsonmap.JSON, error) {
	return s.value, nil
}

func (s *adminSettingsStub) UpdateWithEffects(string, map[string]interface{}) (settingsapp.UpdateResult, error) {
	s.updateCalls++
	return settingsapp.UpdateResult{}, nil
}

func (s *adminSettingsStub) InvalidateCallbackRoutesCache() {}

func TestGenericNotificationSettingsMaskSecretsAndRejectWrites(t *testing.T) {
	setting := settingsmessaging.NotificationCenterDefaultSetting()
	setting.Channels.WeCom.Webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=secret0123456789abcdef"
	stub := &adminSettingsStub{value: jsonmap.JSON(settingsmessaging.NotificationCenterSettingToMap(setting))}
	h := NewAdminHandler(stub)
	rec := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(rec)
	c.Request = httptest.NewRequest("GET", "/settings?key="+constants.SettingKeyNotificationCenterConfig, nil)
	h.Get(c)
	if strings.Contains(rec.Body.String(), "secret0123") || !strings.Contains(rec.Body.String(), `"has_webhook":true`) {
		t.Fatal("secret leak or missing mask")
	}
	rec = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(rec)
	c.Request = httptest.NewRequest("PUT", "/settings", strings.NewReader(`{"key":"`+constants.SettingKeyNotificationCenterConfig+`","value":{"channels":{}}}`))
	c.Request.Header.Set("Content-Type", "application/json")
	h.Update(c)
	if stub.updateCalls != 0 || !strings.Contains(rec.Body.String(), "/admin/settings/notification-center") {
		t.Fatal("generic write bypass")
	}
}

func TestAdminHandlerRejectsGoogleAuthOnGenericUpdate(t *testing.T) {
	gin.SetMode(gin.TestMode)
	stub := &adminSettingsStub{}
	handler := NewAdminHandler(stub)
	recorder := httptest.NewRecorder()
	context, _ := gin.CreateTestContext(recorder)
	context.Request = httptest.NewRequest(
		http.MethodPut,
		"/api/v1/admin/settings",
		strings.NewReader(`{"key":"`+constants.SettingKeyGoogleAuthConfig+`","value":{"enabled":true,"client_id":""}}`),
	)
	context.Request.Header.Set("Content-Type", "application/json")

	handler.Update(context)

	if stub.updateCalls != 0 {
		t.Fatalf("generic update persisted protected Google auth config")
	}
	var body struct {
		StatusCode int    `json:"status_code"`
		Msg        string `json:"msg"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode response %q: %v", recorder.Body.String(), err)
	}
	if recorder.Code != http.StatusOK || body.StatusCode != 400 {
		t.Fatalf("http=%d status_code=%d body=%s", recorder.Code, body.StatusCode, recorder.Body.String())
	}
	if !strings.Contains(body.Msg, "/admin/settings/google-auth") {
		t.Fatalf("unexpected rejection message: %q", body.Msg)
	}
}
