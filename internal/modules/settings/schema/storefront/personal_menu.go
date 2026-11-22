package settingsstorefront

import "github.com/dujiao-next/internal/shared/jsonmap"

// Personal menus control navigation visibility, not route authorization.
func NormalizePersonalMenuJSON(value jsonmap.JSON) jsonmap.JSON {
	sections := []string{"overview", "orders", "wallet", "affiliate", "reseller", "giftCard", "security", "api", "profile"}
	defaults := map[string]bool{"overview": true, "orders": true, "security": true, "profile": true}
	selected := map[string]bool{}
	input, exists := value["enabled_sections"]
	valid := false
	switch items := input.(type) {
	case []interface{}:
		valid = true
		for _, item := range items {
			if key, ok := item.(string); ok {
				selected[key] = true
			}
		}
	case []string:
		valid = true
		for _, key := range items {
			selected[key] = true
		}
	}
	if !exists || !valid {
		selected = defaults
	}
	enabled := make([]string, 0, len(sections))
	for _, key := range sections {
		if selected[key] {
			enabled = append(enabled, key)
		}
	}
	return jsonmap.JSON{"enabled_sections": enabled}
}
