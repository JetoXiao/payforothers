package domain

import (
	"errors"
	"fmt"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/shopspring/decimal"
	"net/mail"
	"strings"
	"unicode"
	"unicode/utf8"
)

var ErrInvalid = errors.New("invoice invalid")
var ErrUnavailable = errors.New("invoice unavailable")
var ErrConflict = errors.New("invoice already requested or order ineligible")
var ErrNotFound = errors.New("invoice not found")

type Config struct {
	Enabled         bool   `json:"enabled"`
	OrdinaryTaxRate string `json:"ordinary_tax_rate"`
	SpecialTaxRate  string `json:"special_tax_rate"`
	SupportWechat   string `json:"support_wechat"`
}

// Empty rates are deliberately not interpreted as zero: activation requires an explicit choice.
func ParseConfig(raw jsonmap.JSON) (Config, error) {
	c := Config{Enabled: true, OrdinaryTaxRate: "3.00", SpecialTaxRate: "8.00", SupportWechat: "think-more-9"}
	if raw == nil {
		return c, nil
	}
	c.Enabled, _ = raw["enabled"].(bool)
	for key, target := range map[string]*string{"ordinary_tax_rate": &c.OrdinaryTaxRate, "special_tax_rate": &c.SpecialTaxRate} {
		if v, ok := raw[key]; ok && v != nil {
			*target = strings.TrimSpace(fmt.Sprint(v))
		}
		if *target == "" {
			if c.Enabled {
				return c, ErrInvalid
			}
			continue
		}
		r, err := decimal.NewFromString(*target)
		if err != nil || r.IsNegative() || r.GreaterThan(decimal.NewFromInt(100)) || !r.Equal(r.Round(2)) {
			return c, ErrInvalid
		}
		*target = r.StringFixed(2)
	}
	if s, ok := raw["support_wechat"].(string); ok {
		c.SupportWechat = strings.TrimSpace(s)
	}
	if len(c.SupportWechat) > 100 || strings.ContainsAny(c.SupportWechat, "\r\n") {
		return c, ErrInvalid
	}
	return c, nil
}
func (c Config) JSON() jsonmap.JSON {
	return jsonmap.JSON{"enabled": c.Enabled, "ordinary_tax_rate": c.OrdinaryTaxRate, "special_tax_rate": c.SpecialTaxRate, "support_wechat": c.SupportWechat}
}
func (c Config) Rate(kind string) (decimal.Decimal, error) {
	if !c.Enabled {
		return decimal.Zero, ErrUnavailable
	}
	raw := c.OrdinaryTaxRate
	if kind == "special" {
		raw = c.SpecialTaxRate
	} else if kind != "ordinary" {
		return decimal.Zero, ErrInvalid
	}
	rate, err := decimal.NewFromString(raw)
	if err != nil {
		return decimal.Zero, ErrInvalid
	}
	return rate, nil
}
func Tax(base, rate decimal.Decimal) decimal.Decimal {
	return base.Mul(rate).Div(decimal.NewFromInt(100)).Round(2)
}

// Profiles capture company identity only. Invoice kind is selected per application.
func NormalizeProfile(p *Profile, special bool) error {
	if p == nil {
		return ErrInvalid
	}
	fields := []struct {
		value    *string
		max      int
		required bool
	}{
		{&p.Name, 200, true}, {&p.TaxpayerID, 100, true}, {&p.Address, 500, special}, {&p.Phone, 80, special},
		{&p.BankName, 200, special}, {&p.BankAccount, 100, special}, {&p.Email, 254, true},
	}
	for _, field := range fields {
		*field.value = strings.TrimSpace(*field.value)
		if (field.required && *field.value == "") || utf8.RuneCountInString(*field.value) > field.max || strings.IndexFunc(*field.value, unicode.IsControl) >= 0 {
			return ErrInvalid
		}
	}
	p.TaxpayerID = strings.ToUpper(p.TaxpayerID)
	for _, r := range p.TaxpayerID {
		if !(r >= '0' && r <= '9' || r >= 'A' && r <= 'Z') {
			return ErrInvalid
		}
	}
	a, err := mail.ParseAddress(p.Email)
	if err != nil || a.Address != p.Email {
		return ErrInvalid
	}
	p.Type = "company"
	return nil
}
func Snapshot(p *Profile) jsonmap.JSON {
	return jsonmap.JSON{"name": p.Name, "taxpayer_id": p.TaxpayerID, "address": p.Address, "phone": p.Phone, "bank_name": p.BankName, "bank_account": p.BankAccount, "email": p.Email}
}
