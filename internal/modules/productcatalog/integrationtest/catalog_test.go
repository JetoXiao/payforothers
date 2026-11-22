package integrationtest

import (
	"fmt"
	cardsecret "github.com/dujiao-next/internal/modules/cardsecret/domain"
	productdomain "github.com/dujiao-next/internal/modules/catalog/product/domain"
	catalogcontract "github.com/dujiao-next/internal/modules/productcatalog/contract"
	catalogdomain "github.com/dujiao-next/internal/modules/productcatalog/domain"
	catalogstore "github.com/dujiao-next/internal/modules/productcatalog/infrastructure/gormstore"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/dujiao-next/internal/shared/money"
	"github.com/glebarez/sqlite"
	"github.com/shopspring/decimal"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
	"testing"
	"time"
)

func TestSyncPreservesManualPriceAndReportsProfitInventory(t *testing.T) {
	db, err := gorm.Open(sqlite.Open(fmt.Sprintf("file:product-catalog-%d?mode=memory&cache=shared", time.Now().UnixNano())), &gorm.Config{})
	require.NoError(t, err)
	sql, _ := db.DB()
	sql.SetMaxOpenConns(1)
	sql.SetMaxIdleConns(1)
	require.NoError(t, db.AutoMigrate(&productdomain.Product{}, &productdomain.ProductSKU{}, &cardsecret.Secret{}))
	require.NoError(t, db.Exec("DROP TABLE IF EXISTS product_catalog_items").Error)
	require.NoError(t, db.AutoMigrate(&catalogdomain.Item{}))
	p := productdomain.Product{Slug: "demo", TitleJSON: jsonmap.JSON{"zh-CN": "Demo"}, PriceAmount: money.FromDecimal(decimal.NewFromInt(20)), IsActive: true}
	require.NoError(t, db.Create(&p).Error)
	sku := productdomain.ProductSKU{ProductID: p.ID, SKUCode: "A", PriceAmount: money.FromDecimal(decimal.NewFromInt(20)), CostPriceAmount: money.FromDecimal(decimal.NewFromInt(8)), ManualStockTotal: 3, ManualStockLocked: 1, IsActive: true}
	require.NoError(t, db.Create(&sku).Error)
	cs := catalogstore.New(db)
	n, err := cs.Sync(false)
	require.NoError(t, err)
	require.Equal(t, 1, n)
	rows, total, err := cs.List(catalogcontract.Filter{Page: 1, PageSize: 20})
	require.NoError(t, err)
	require.EqualValues(t, 1, total)
	require.Len(t, rows, 1)
	item := rows[0]
	require.Equal(t, "20.00", item.SalePrice.StringFixed(2))
	_, err = cs.Update(item.ID, map[string]interface{}{"cost_price": "11.00", "sale_price": "18.00", "follow_product_price": false})
	require.NoError(t, err)
	sku.PriceAmount = money.FromDecimal(decimal.NewFromInt(30))
	require.NoError(t, db.Save(&sku).Error)
	_, err = cs.Sync(false)
	require.NoError(t, err)
	rows, _, err = cs.List(catalogcontract.Filter{Page: 1, PageSize: 20})
	require.NoError(t, err)
	item = rows[0]
	require.Equal(t, "18.00", item.SalePrice.StringFixed(2))
	require.Equal(t, "7.00", item.ProfitAmount().StringFixed(2))
	require.Equal(t, int64(2), item.Inventory())
}
