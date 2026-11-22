package settingsapp

import (
	"reflect"
	"testing"

	"github.com/dujiao-next/internal/constants"
)

func TestWechatAccountsNormalization(t *testing.T) {
	for _, tc := range []struct {
		name  string
		input interface{}
		want  []string
	}{
		{"missing", nil, []string{}},
		{"malformed", "account1", []string{}},
		{"empty", []interface{}{}, []string{}},
		{"single", []string{" think-more-9 "}, []string{"think-more-9"}},
		{"multiple", []interface{}{"account_1", "account-2"}, []string{"account_1", "account-2"}},
		{"invalid and duplicates", []interface{}{"", "account_1", "ACCOUNT_1", 123, "<script>", "https://example.com", "account-2"}, []string{"account_1", "account-2"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := normalizeWechatAccounts(tc.input); !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("got %v want %v", got, tc.want)
			}
		})
	}
}

func TestWechatSupportSettingRoundtripAndClear(t *testing.T) {
	svc := NewService(newMockSettingRepo())
	for _, accounts := range [][]interface{}{{"first", "second"}, {"first"}, {}} {
		result, err := svc.UpdateWithEffects(constants.SettingKeySiteConfig, map[string]interface{}{
			"contact": map[string]interface{}{"telegram": "https://t.me/demo", "whatsapp": "", "wechat": accounts},
		})
		if err != nil {
			t.Fatal(err)
		}
		if !result.HasEffect(EffectInvalidatePublicConfigCache) {
			t.Fatal("public config cache must be invalidated")
		}
		config, err := svc.GetConfig(map[string]interface{}{})
		if err != nil {
			t.Fatal(err)
		}
		contact := config["contact"].(map[string]interface{})
		if contact["telegram"] != "https://t.me/demo" {
			t.Fatal("unrelated contact changed")
		}
		if got := normalizeWechatAccounts(contact["wechat"]); len(got) != len(accounts) {
			t.Fatalf("unexpected public contacts: %v", got)
		}
	}
}
