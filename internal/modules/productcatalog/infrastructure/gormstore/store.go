package gormstore

import (
	"errors"
	cardsecret "github.com/dujiao-next/internal/modules/cardsecret/domain"
	productdomain "github.com/dujiao-next/internal/modules/catalog/product/domain"
	productcontract "github.com/dujiao-next/internal/modules/productcatalog/contract"
	productcatalog "github.com/dujiao-next/internal/modules/productcatalog/domain"
	"github.com/dujiao-next/internal/shared/money"
	"gorm.io/gorm"
	"strings"
	"time"
)

type Store struct{ db *gorm.DB }

func New(db *gorm.DB) *Store { return &Store{db: db} }
func (s *Store) List(f productcontract.Filter) ([]productcatalog.Item, int64, error) {
	q := s.db.Model(&productcatalog.Item{}).Where("excluded = ?", false)
	if f.Search != "" {
		like := "%" + strings.TrimSpace(f.Search) + "%"
		q = q.Where("product_slug LIKE ? OR sku_code LIKE ? OR title_json LIKE ?", like, like, like)
	}
	if f.ProductActive != nil {
		if *f.ProductActive {
			q = q.Where("product_active = ? AND sku_active = ?", true, true)
		} else {
			q = q.Where("product_active = ? OR sku_active = ?", false, false)
		}
	}
	if f.FollowPrice != nil {
		q = q.Where("follow_product_price = ?", *f.FollowPrice)
	}
	var total int64
	if err := q.Count(&total).Error; err != nil {
		return nil, 0, err
	}
	if f.Page < 1 {
		f.Page = 1
	}
	if f.PageSize < 1 || f.PageSize > 100 {
		f.PageSize = 20
	}
	rows := []productcatalog.Item{}
	err := q.Order("product_active DESC, product_id ASC, sku_id ASC").Offset((f.Page - 1) * f.PageSize).Limit(f.PageSize).Find(&rows).Error
	return rows, total, err
}
func (s *Store) Sync(includeInactive bool) (int, error) {
	q := s.db.Model(&productdomain.Product{}).Where("products.deleted_at IS NULL").Preload("SKUs", func(db *gorm.DB) *gorm.DB { return db.Where("deleted_at IS NULL").Order("id") })
	products := []productdomain.Product{}
	if err := q.Find(&products).Error; err != nil {
		return 0, err
	}
	count := 0
	for _, p := range products {
		for _, sku := range p.SKUs {
			var item productcatalog.Item
			err := s.db.Where("product_id = ? AND sku_id = ?", p.ID, sku.ID).First(&item).Error
			if errors.Is(err, gorm.ErrRecordNotFound) {
				if !includeInactive && (!p.IsActive || !sku.IsActive) {
					continue
				}
				item = productcatalog.Item{ProductID: p.ID, SKUID: sku.ID, CostPrice: sku.CostPriceAmount, SalePrice: sku.PriceAmount, FollowProductPrice: true, CreatedAt: time.Now()}
			} else if err != nil {
				return count, err
			} else if item.Excluded {
				continue
			}
			item.ProductSlug = p.Slug
			item.TitleJSON = p.TitleJSON
			item.ImagesJSON = p.Images
			item.SKUCode = sku.SKUCode
			item.SpecValuesJSON = sku.SpecValuesJSON
			item.ProductActive = p.IsActive
			item.SKUActive = sku.IsActive
			item.ProductPrice = sku.PriceAmount
			item.ManualStock = sku.ManualStockTotal
			item.ManualLocked = sku.ManualStockLocked
			item.ManualSold = sku.ManualStockSold
			item.UpdatedAt = time.Now()
			if item.FollowProductPrice {
				item.SalePrice = sku.PriceAmount
			}
			var auto int64
			s.db.Model(&cardsecret.Secret{}).Where("product_id = ? AND sku_id = ? AND status = ? AND deleted_at IS NULL", p.ID, sku.ID, cardsecret.StatusAvailable).Count(&auto)
			item.AutoStock = auto
			if err := s.db.Save(&item).Error; err != nil {
				return count, err
			}
			count++
		}
	}
	return count, nil
}

func (s *Store) Delete(id uint) error {
	if id == 0 {
		return errors.New("invalid catalog item")
	}
	result := s.db.Model(&productcatalog.Item{}).Where("id = ? AND excluded = ?", id, false).Update("excluded", true)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
func (s *Store) Update(id uint, fields map[string]interface{}) (*productcatalog.Item, error) {
	if id == 0 || len(fields) == 0 {
		return nil, errors.New("invalid catalog item")
	}
	if err := s.db.Model(&productcatalog.Item{}).Where("id = ?", id).Updates(fields).Error; err != nil {
		return nil, err
	}
	var item productcatalog.Item
	if err := s.db.First(&item, id).Error; err != nil {
		return nil, err
	}
	return &item, nil
}

var _ productcontract.Store = (*Store)(nil)
var _ = money.Amount{}
