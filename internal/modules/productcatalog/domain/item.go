package domain

import (
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/dujiao-next/internal/shared/money"
	"github.com/shopspring/decimal"
	"time"
)

type Item struct {
	ID                 uint         `gorm:"primarykey" json:"id"`
	ProductID          uint         `gorm:"uniqueIndex:idx_catalog_product_sku;not null" json:"product_id"`
	SKUID              uint         `gorm:"column:sku_id;uniqueIndex:idx_catalog_product_sku;not null" json:"sku_id"`
	ProductSlug        string       `gorm:"size:160;index" json:"product_slug"`
	TitleJSON          jsonmap.JSON `gorm:"type:json" json:"title"`
	SKUCode            string       `gorm:"size:64;index" json:"sku_code"`
	SpecValuesJSON     jsonmap.JSON `gorm:"type:json" json:"spec_values"`
	ProductActive      bool         `gorm:"index" json:"product_active"`
	SKUActive          bool         `gorm:"index" json:"sku_active"`
	ProductPrice       money.Amount `gorm:"type:decimal(20,2);not null;default:0" json:"product_price"`
	CostPrice          money.Amount `gorm:"type:decimal(20,2);not null;default:0" json:"cost_price"`
	SalePrice          money.Amount `gorm:"type:decimal(20,2);not null;default:0" json:"sale_price"`
	FollowProductPrice bool         `gorm:"not null;default:true" json:"follow_product_price"`
	ManualStock        int          `gorm:"not null;default:0" json:"manual_stock"`
	ManualLocked       int          `gorm:"not null;default:0" json:"manual_locked"`
	ManualSold         int          `gorm:"not null;default:0" json:"manual_sold"`
	AutoStock          int64        `gorm:"not null;default:0" json:"auto_stock"`
	UpdatedAt          time.Time    `json:"updated_at"`
	CreatedAt          time.Time    `json:"created_at"`
}

func (Item) TableName() string { return "product_catalog_items" }

func (i Item) EffectiveSalePrice() money.Amount {
	if i.FollowProductPrice {
		return i.ProductPrice
	}
	return i.SalePrice
}
func (i Item) ProfitAmount() money.Amount {
	return money.FromDecimal(i.EffectiveSalePrice().Decimal.Sub(i.CostPrice.Decimal))
}
func (i Item) ProfitRate() float64 {
	if i.EffectiveSalePrice().Decimal.IsZero() {
		return 0
	}
	return i.ProfitAmount().Decimal.Div(i.EffectiveSalePrice().Decimal).Mul(decimal.NewFromInt(100)).InexactFloat64()
}
func (i Item) Inventory() int64 {
	if i.AutoStock >= 0 {
		return i.AutoStock + int64(maxInt(i.ManualStock-i.ManualLocked, 0))
	}
	return -1
}
func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
