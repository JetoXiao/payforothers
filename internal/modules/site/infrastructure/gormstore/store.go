package gormstore

import (
	"errors"
	"time"

	admindomain "github.com/dujiao-next/internal/modules/identity/admin/domain"
	userdomain "github.com/dujiao-next/internal/modules/identity/user/domain"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	resellerdomain "github.com/dujiao-next/internal/modules/reseller/domain"
	sitecontract "github.com/dujiao-next/internal/modules/site/contract"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type Store struct{ db *gorm.DB }

func New(db *gorm.DB) *Store { return &Store{db: db} }
func (s *Store) FindDomain(host string) (*sitedomain.Site, error) {
	var site sitedomain.Site
	err := s.db.Where("domain = ?", host).First(&site).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &site, err
}
func (s *Store) ListSites() ([]sitedomain.Site, error) {
	rows := []sitedomain.Site{}
	err := s.db.Order("id").Find(&rows).Error
	return rows, err
}
func (s *Store) DomainInUse(host string) (bool, error) {
	var n int64
	if err := s.db.Model(&sitedomain.Site{}).Where("domain = ?", host).Count(&n).Error; err != nil || n > 0 {
		return n > 0, err
	}
	if s.db.Migrator().HasTable(&resellerdomain.Domain{}) {
		err := s.db.Model(&resellerdomain.Domain{}).Where("domain = ?", host).Count(&n).Error
		return n > 0, err
	}
	return false, nil
}
func (s *Store) SaveSite(site *sitedomain.Site) error {
	if site.ID == 0 {
		enabled := site.Enabled
		return s.db.Transaction(func(tx *gorm.DB) error {
			if err := tx.Select("Name", "Domain", "Enabled", "CreatedAt", "UpdatedAt").Create(site).Error; err != nil {
				return err
			}
			// GORM's boolean default must not turn an explicitly disabled site on.
			site.Enabled = enabled
			return tx.Model(site).Update("enabled", enabled).Error
		})
	}
	return s.db.Transaction(func(tx *gorm.DB) error {
		var current sitedomain.Site
		if err := tx.First(&current, site.ID).Error; err != nil {
			return err
		}
		if site.Domain != "" && site.Domain != current.Domain {
			return errors.New("site domain is immutable")
		}
		if err := tx.Model(&current).Updates(map[string]interface{}{"name": site.Name, "enabled": site.Enabled, "updated_at": time.Now()}).Error; err != nil {
			return err
		}
		site.Domain = current.Domain
		return nil
	})
}
func (s *Store) AdminExists(id uint) (bool, error) {
	var n int64
	err := s.db.Model(&admindomain.Admin{}).Where("id = ? AND deleted_at IS NULL AND is_super = ?", id, false).Count(&n).Error
	return n == 1, err
}
func (s *Store) GetScope(id uint) (sitedomain.Scope, error) {
	result := sitedomain.Scope{Grants: []sitedomain.Grant{}}
	var n int64
	if err := s.db.Model(&sitedomain.AdminScope{}).Where("admin_id = ?", id).Count(&n).Error; err != nil {
		return result, err
	}
	result.Restricted = n > 0
	if !result.Restricted {
		return result, nil
	}
	err := s.db.Where("admin_id = ?", id).Order("site_id").Find(&result.Grants).Error
	return result, err
}
func (s *Store) SetGrants(id uint, grants []sitedomain.Grant) error {
	return s.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Clauses(clause.OnConflict{UpdateAll: true}).Create(&sitedomain.AdminScope{AdminID: id, UpdatedAt: time.Now()}).Error; err != nil {
			return err
		}
		if err := tx.Where("admin_id = ?", id).Delete(&sitedomain.Grant{}).Error; err != nil {
			return err
		}
		if len(grants) > 0 {
			return tx.Create(&grants).Error
		}
		return nil
	})
}
func (s *Store) RecordVisit(v sitedomain.Visit) error {
	if v.ClientIP != "" {
		var recent sitedomain.Visit
		cutoff := v.LastSeenAt.Add(-60 * time.Minute)
		if err := s.db.Where("site_id = ? AND client_ip = ? AND last_seen_at >= ?", v.SiteID, v.ClientIP, cutoff).Order("last_seen_at DESC").First(&recent).Error; err == nil {
			updates := map[string]interface{}{"last_seen_at": v.LastSeenAt}
			if v.UserID > 0 {
				updates["user_id"] = v.UserID
			}
			if v.Region != "" {
				updates["region"] = v.Region
			}
			return s.db.Model(&recent).Updates(updates).Error
		} else if !errors.Is(err, gorm.ErrRecordNotFound) {
			return err
		}
	}
	return s.db.Clauses(clause.OnConflict{Columns: []clause.Column{{Name: "site_id"}, {Name: "day"}, {Name: "visitor_hash"}, {Name: "user_id"}}, DoUpdates: clause.Assignments(map[string]interface{}{"last_seen_at": v.LastSeenAt})}).Create(&v).Error
}
func siteQuery(q *gorm.DB, col string, f sitecontract.Filter) *gorm.DB {
	if f.SiteID != nil {
		q = q.Where(col+" = ?", *f.SiteID)
	}
	return q
}
func window(q *gorm.DB, col string, f sitecontract.Filter) *gorm.DB {
	return q.Where(col+" >= ? AND "+col+" < ?", f.From, f.To)
}
func paging(q *gorm.DB, f sitecontract.Filter) *gorm.DB {
	return q.Offset((f.Page - 1) * f.PageSize).Limit(f.PageSize)
}
func (s *Store) ListUsers(f sitecontract.Filter) ([]sitecontract.UserRow, int64, error) {
	q := window(siteQuery(s.db.Model(&userdomain.User{}).Where("deleted_at IS NULL"), "registration_site_id", f), "created_at", f)
	if f.Keyword != "" {
		q = q.Where("email LIKE ? OR display_name LIKE ?", "%"+f.Keyword+"%", "%"+f.Keyword+"%")
	}
	var n int64
	if err := q.Count(&n).Error; err != nil {
		return nil, 0, err
	}
	rows := []sitecontract.UserRow{}
	err := paging(q.Select("id,email,display_name,registration_site_id,registration_domain,created_at").Order("id DESC"), f).Scan(&rows).Error
	return rows, n, err
}

func (s *Store) AssignUserSite(userID, siteID uint) error {
	var domain string
	if siteID > 0 {
		var site sitedomain.Site
		if err := s.db.First(&site, siteID).Error; err != nil {
			return err
		}
		domain = site.Domain
	}
	result := s.db.Model(&userdomain.User{}).Where("id = ? AND deleted_at IS NULL", userID).Updates(map[string]interface{}{
		"registration_site_id": siteID,
		"registration_domain":  domain,
		"updated_at":           time.Now(),
	})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
func (s *Store) orderQuery(f sitecontract.Filter) *gorm.DB {
	q := window(siteQuery(s.db.Model(&orderdomain.Order{}).Where("orders.deleted_at IS NULL AND orders.parent_id IS NULL AND orders.purpose <> 'invoice_tax'"), "orders.source_site_id", f), "orders.created_at", f)
	if f.Keyword != "" {
		q = q.Where("orders.order_no LIKE ?", "%"+f.Keyword+"%")
	}
	if f.Status != "" {
		q = q.Where("orders.status = ?", f.Status)
	}
	return q
}
func orderSelect(q *gorm.DB) *gorm.DB {
	return q.Select("orders.id,orders.order_no,orders.source_site_id,orders.source_domain,orders.user_id,COALESCE(NULLIF(orders.guest_email,''),users.email,'') AS buyer_email,orders.status,orders.currency,orders.total_amount,orders.refunded_amount,orders.created_at").Joins("LEFT JOIN users ON users.id = orders.user_id AND users.deleted_at IS NULL")
}
func (s *Store) ListOrders(f sitecontract.Filter) ([]sitecontract.OrderRow, int64, error) {
	q := s.orderQuery(f)
	var n int64
	if err := q.Count(&n).Error; err != nil {
		return nil, 0, err
	}
	rows := []sitecontract.OrderRow{}
	err := paging(orderSelect(q).Order("orders.id DESC"), f).Scan(&rows).Error
	return rows, n, err
}

func (s *Store) AssignOrderSite(orderID, siteID uint) error {
	var domain string
	if siteID > 0 {
		var site sitedomain.Site
		if err := s.db.First(&site, siteID).Error; err != nil {
			return err
		}
		domain = site.Domain
	}
	result := s.db.Model(&orderdomain.Order{}).
		Where("deleted_at IS NULL AND (id = ? OR parent_id = ?)", orderID, orderID).
		Updates(map[string]interface{}{"source_site_id": siteID, "source_domain": domain})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return gorm.ErrRecordNotFound
	}
	return nil
}
func (s *Store) GetOrder(id uint, f sitecontract.Filter) (*sitecontract.OrderRow, error) {
	var row sitecontract.OrderRow
	if err := orderSelect(s.orderQuery(f).Where("orders.id = ?", id)).Take(&row).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil
		}
		return nil, err
	}
	var items []orderdomain.OrderItem
	err := s.db.Model(&orderdomain.OrderItem{}).Select("order_items.title_json,order_items.quantity").Joins("JOIN orders ON orders.id = order_items.order_id").Where("order_items.deleted_at IS NULL AND orders.deleted_at IS NULL AND (orders.id = ? OR orders.parent_id = ?) AND orders.source_site_id = ?", id, id, row.SourceSiteID).Find(&items).Error
	row.Items = []sitecontract.OrderItemRow{}
	for _, i := range items {
		row.Items = append(row.Items, sitecontract.OrderItemRow{Title: i.TitleJSON, Quantity: i.Quantity})
	}
	return &row, err
}
func (s *Store) ListVisits(f sitecontract.Filter) ([]sitedomain.Visit, int64, error) {
	q := window(siteQuery(s.db.Model(&sitedomain.Visit{}), "storefront_visits.site_id", f), "storefront_visits.first_seen_at", f)
	var n int64
	if err := q.Count(&n).Error; err != nil {
		return nil, 0, err
	}
	type visitRow struct {
		ID          uint
		SiteID      uint
		Domain      string
		Day         string
		VisitorHash string
		UserID      uint
		UserEmail   string
		ClientIP    string
		Region      string
		FirstSeenAt time.Time
		LastSeenAt  time.Time
	}
	rows := []visitRow{}
	err := paging(q.Select("storefront_visits.*, COALESCE(users.email, '') AS user_email").Joins("LEFT JOIN users ON users.id = storefront_visits.user_id AND users.deleted_at IS NULL").Order("storefront_visits.id DESC"), f).Scan(&rows).Error
	out := make([]sitedomain.Visit, 0, len(rows))
	for _, row := range rows {
		out = append(out, sitedomain.Visit{ID: row.ID, SiteID: row.SiteID, Domain: row.Domain, Day: row.Day, VisitorHash: row.VisitorHash, UserID: row.UserID, UserEmail: row.UserEmail, ClientIP: row.ClientIP, Region: row.Region, FirstSeenAt: row.FirstSeenAt, LastSeenAt: row.LastSeenAt})
	}
	return out, n, err
}

var _ sitecontract.Store = (*Store)(nil)
