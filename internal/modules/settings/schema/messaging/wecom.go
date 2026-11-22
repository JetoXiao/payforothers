package settingsmessaging

import (
	"fmt"
	"net/url"
	"regexp"
)

// WeCom is intentionally limited to newly created orders. Other notification
// scenes and their potentially sensitive delivery summaries are not forwarded.
type WeComNotificationSetting struct {
	Enabled bool   `json:"enabled"`
	Webhook string `json:"webhook"`
}

type WeComNotificationPatch struct {
	Enabled      *bool   `json:"enabled"`
	Webhook      *string `json:"webhook"`
	ClearWebhook bool    `json:"clear_webhook"`
}

var wecomKeyPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{16,128}$`)

// ValidateWeComWebhook allows only Tencent's bot endpoint, never arbitrary URLs.
// Errors deliberately do not include the secret URL.
func ValidateWeComWebhook(raw string) error {
	u, err := url.Parse(raw)
	if err == nil && u.Scheme == "https" && u.Host == "qyapi.weixin.qq.com" &&
		u.User == nil && u.Fragment == "" && u.Path == "/cgi-bin/webhook/send" && u.RawPath == "" {
		q, queryErr := url.ParseQuery(u.RawQuery)
		if queryErr == nil && len(q) == 1 && len(q["key"]) == 1 && wecomKeyPattern.MatchString(q.Get("key")) {
			return nil
		}
	}
	return fmt.Errorf("%w: 企业微信 Webhook 格式无效，请使用企业微信群机器人的 HTTPS 地址", ErrNotificationConfigInvalid)
}
