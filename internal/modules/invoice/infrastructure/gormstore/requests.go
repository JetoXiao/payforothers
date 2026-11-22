package gormstore

import (
	"errors"
	"github.com/dujiao-next/internal/constants"
	d "github.com/dujiao-next/internal/modules/invoice/domain"
	od "github.com/dujiao-next/internal/modules/order/domain"
	settings "github.com/dujiao-next/internal/modules/settings/infrastructure/gormstore"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/dujiao-next/internal/shared/money"
	"github.com/dujiao-next/internal/shared/serial"
	"github.com/shopspring/decimal"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
	"strings"
	"time"
	"unicode"
)

func paidEligible(o *od.Order) bool {
	if o.PaidAt == nil || o.RefundedAmount.Decimal.IsPositive() || o.DeletedAt != nil {
		return false
	}
	switch o.Status {
	case "paid", "fulfilling", "partially_delivered", "delivered", "completed":
		return true
	}
	return false
}
func lockOrders(tx *gorm.DB, nos []string, user uint) ([]od.Order, error) {
	rows := []od.Order{}
	err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where("order_no IN ? AND user_id = ? AND parent_id IS NULL AND reseller_id IS NULL AND deleted_at IS NULL AND purpose <> ?", nos, user, "invoice_tax").Order("id").Find(&rows).Error
	if err != nil {
		return nil, err
	}
	if len(rows) != len(nos) {
		return nil, d.ErrNotFound
	}
	return rows, nil
}
func lockRequestSources(tx *gorm.DB, r *d.Request) ([]od.Order, error) {
	var links []d.OrderLink
	if err := tx.Where("request_id = ?", r.ID).Find(&links).Error; err != nil {
		return nil, err
	}
	ids := []uint{}
	for _, link := range links {
		ids = append(ids, link.OrderID)
	}
	rows := []od.Order{}
	if len(ids) == 0 {
		return nil, d.ErrConflict
	}
	err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where("id IN ? AND user_id = ? AND deleted_at IS NULL", ids, r.UserID).Order("id").Find(&rows).Error
	if err != nil {
		return nil, err
	}
	if len(rows) != len(ids) {
		return nil, d.ErrConflict
	}
	return rows, nil
}

// Apply computes all amounts server-side and claims every source order atomically.
func (s *RequestStore) Apply(user, profileID uint, kind string, nos []string, preview bool) (*d.Request, error) {
	if user == 0 || profileID == 0 || len(nos) == 0 || len(nos) > 50 {
		return nil, d.ErrInvalid
	}
	seen := map[string]bool{}
	for i, n := range nos {
		n = strings.TrimSpace(n)
		if n == "" || len(n) > 80 || seen[n] {
			return nil, d.ErrInvalid
		}
		seen[n] = true
		nos[i] = n
	}
	var result *d.Request
	err := s.db.Transaction(func(tx *gorm.DB) error {
		var setting settings.SettingRecord
		if err := tx.Where("key = ?", constants.SettingKeyInvoiceConfig).First(&setting).Error; err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				setting.ValueJSON = jsonmap.JSON{"enabled": true, "ordinary_tax_rate": "3.00", "special_tax_rate": "8.00", "support_wechat": "think-more-9"}
			} else {
				return err
			}
		}
		cfg, err := d.ParseConfig(setting.ValueJSON)
		if err != nil {
			return err
		}
		rate, err := cfg.Rate(kind)
		if err != nil {
			return err
		}
		profile, err := New(tx).GetByIDAndUser(profileID, user)
		if err != nil {
			return err
		}
		if profile == nil {
			return d.ErrNotFound
		}
		if err = d.NormalizeProfile(profile, kind == "special"); err != nil {
			return err
		}
		orders, err := lockOrders(tx, nos, user)
		if err != nil {
			return err
		}
		base := decimal.Zero
		currency := orders[0].Currency
		ids := []uint{}
		for _, o := range orders {
			if !paidEligible(&o) || o.InvoiceRequested || o.InvoiceRequestID != nil || o.InvoiceStatus != "none" && o.InvoiceStatus != "" || o.Currency != currency || o.SourceSiteID != orders[0].SourceSiteID {
				return d.ErrConflict
			}
			base = base.Add(o.TotalAmount.Decimal)
			ids = append(ids, o.ID)
		}
		tax := d.Tax(base, rate)
		request := &d.Request{UserID: user, InvoiceType: kind, Currency: currency, OrderIDs: jsonmap.JSON{"ids": ids}, OrderNos: jsonmap.JSON{"numbers": nos}, ProfileSnapshot: d.Snapshot(profile), Email: profile.Email, TaxRate: money.FromDecimal(rate), TaxBaseAmount: money.FromDecimal(base), TaxAmount: money.FromDecimal(tax), Status: d.StatusPendingTaxPayment}
		if tax.IsZero() {
			request.Status = d.StatusProcessing
		}
		result = request
		if preview {
			return nil
		}
		if err := tx.Create(request).Error; err != nil {
			return err
		}
		if tax.IsPositive() {
			expires := time.Now().Add(30 * time.Minute)
			order := &od.Order{SourceSiteID: orders[0].SourceSiteID, SourceDomain: orders[0].SourceDomain, OrderNo: serial.Generate("INV"), UserID: user, Status: constants.OrderStatusPendingPayment, Purpose: "invoice_tax", Currency: currency, OriginalAmount: money.FromDecimal(tax), TotalAmount: money.FromDecimal(tax), OnlinePaidAmount: money.FromDecimal(tax), InvoiceRequestID: &request.ID, InvoiceStatus: "none", ExpiresAt: &expires}
			if err := tx.Create(order).Error; err != nil {
				return err
			}
			request.PaymentOrderID = &order.ID
			request.PaymentOrderNo = order.OrderNo
			if err := tx.Save(request).Error; err != nil {
				return err
			}
		}
		for _, order := range orders {
			if err := tx.Create(&d.OrderLink{OrderID: order.ID, RequestID: request.ID}).Error; err != nil {
				return d.ErrConflict
			}
			claimed := tx.Model(&od.Order{}).Where("id = ? AND invoice_requested = ? AND invoice_request_id IS NULL", order.ID, false).Updates(map[string]interface{}{"invoice_requested": true, "invoice_request_id": request.ID, "invoice_status": request.Status, "invoice_type": kind, "updated_at": time.Now()})
			if claimed.Error != nil {
				return claimed.Error
			}
			if claimed.RowsAffected != 1 {
				return d.ErrConflict
			}
		}
		return nil
	})
	return result, err
}

// CreateForCheckout participates in the existing order-creation transaction.
func CreateForCheckout(tx *gorm.DB, o *od.Order) error {
	if !o.InvoiceRequested || o.ParentID != nil || o.Purpose == "invoice_tax" {
		return nil
	}
	email, _ := o.InvoiceProfileSnapshot["email"].(string)
	r := &d.Request{UserID: o.UserID, InvoiceType: o.InvoiceType, Currency: o.Currency, OrderIDs: jsonmap.JSON{"ids": []uint{o.ID}}, OrderNos: jsonmap.JSON{"numbers": []string{o.OrderNo}}, ProfileSnapshot: o.InvoiceProfileSnapshot, Email: email, TaxRate: o.InvoiceTaxRate, TaxBaseAmount: o.InvoiceTaxBaseAmount, TaxAmount: o.InvoiceTaxAmount, Status: d.StatusPendingTaxPayment, PaymentOrderID: &o.ID, PaymentOrderNo: o.OrderNo}
	if err := tx.Create(r).Error; err != nil {
		return err
	}
	if err := tx.Create(&d.OrderLink{OrderID: o.ID, RequestID: r.ID}).Error; err != nil {
		return err
	}
	o.InvoiceRequestID = &r.ID
	return tx.Model(o).Update("invoice_request_id", r.ID).Error
}

// OnPaid is called only after a verified payment/wallet settlement in the same transaction.
func OnPaid(tx *gorm.DB, o *od.Order, at time.Time) error {
	if o.InvoiceRequestID == nil {
		return nil
	}
	var r d.Request
	if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&r, *o.InvoiceRequestID).Error; err != nil {
		return err
	}
	if r.PaymentOrderID == nil || *r.PaymentOrderID != o.ID {
		return d.ErrConflict
	}
	if r.Status != d.StatusPendingTaxPayment {
		return nil
	}
	sources, err := lockRequestSources(tx, &r)
	if err != nil {
		return err
	}
	status := d.StatusProcessing
	for _, source := range sources {
		if source.ID != o.ID && !paidEligible(&source) {
			status = d.StatusReview
		}
	}
	if err := tx.Model(&r).Updates(map[string]interface{}{"status": status, "updated_at": at}).Error; err != nil {
		return err
	}
	for _, source := range sources {
		if err := tx.Model(&od.Order{}).Where("id = ?", source.ID).Update("invoice_status", status).Error; err != nil {
			return err
		}
	}
	o.InvoiceStatus = status
	return nil
}

// Only an unpaid, canceled order releases a reservation; issued records stay immutable.
func OnCanceled(tx *gorm.DB, o *od.Order, at time.Time) error {
	if o.InvoiceRequestID == nil || o.PaidAt != nil {
		return nil
	}
	var r d.Request
	if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&r, *o.InvoiceRequestID).Error; err != nil {
		return err
	}
	if r.PaymentOrderID == nil || *r.PaymentOrderID != o.ID || r.Status != d.StatusPendingTaxPayment {
		return nil
	}
	if err := tx.Model(&r).Updates(map[string]interface{}{"status": d.StatusCanceled, "updated_at": at}).Error; err != nil {
		return err
	}
	if o.Purpose == "invoice_tax" {
		if err := tx.Model(&od.Order{}).Where("invoice_request_id = ? AND id <> ?", r.ID, o.ID).Updates(map[string]interface{}{"invoice_requested": false, "invoice_request_id": nil, "invoice_status": "none", "invoice_type": ""}).Error; err != nil {
			return err
		}
	} else {
		if err := tx.Model(o).Update("invoice_status", d.StatusCanceled).Error; err != nil {
			return err
		}
	}
	return tx.Where("request_id = ?", r.ID).Delete(&d.OrderLink{}).Error
}

func (s *RequestStore) list(user uint, page, size int) ([]d.Request, int64, error) {
	if page < 1 {
		page = 1
	}
	if size < 1 || size > 100 {
		size = 20
	}
	q := s.db.Model(&d.Request{})
	if user > 0 {
		q = q.Where("user_id = ?", user)
	}
	var count int64
	if err := q.Count(&count).Error; err != nil {
		return nil, 0, err
	}
	rows := []d.Request{}
	err := q.Order("id DESC").Offset((page - 1) * size).Limit(size).Find(&rows).Error
	return rows, count, err
}
func (s *RequestStore) ListByUser(user uint, page, size int) ([]d.Request, int64, error) {
	if user == 0 {
		return nil, 0, d.ErrInvalid
	}
	return s.list(user, page, size)
}
func (s *RequestStore) ListAdmin(page, size int) ([]d.Request, int64, error) {
	return s.list(0, page, size)
}

func (s *RequestStore) MarkIssued(id, admin uint, number string) (*d.Request, error) {
	number = strings.TrimSpace(number)
	if id == 0 || admin == 0 || number == "" || len(number) > 120 || strings.IndexFunc(number, unicode.IsControl) >= 0 {
		return nil, d.ErrInvalid
	}
	var result d.Request
	err := s.db.Transaction(func(tx *gorm.DB) error {
		if err := tx.First(&result, id).Error; err != nil {
			return d.ErrNotFound
		}
		if result.PaymentOrderID != nil {
			var payer od.Order
			if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&payer, *result.PaymentOrderID).Error; err != nil {
				return err
			}
			if !paidEligible(&payer) {
				return d.ErrConflict
			}
		}
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&result, id).Error; err != nil {
			return err
		}
		if result.Status != d.StatusProcessing {
			return d.ErrConflict
		}
		sources, err := lockRequestSources(tx, &result)
		if err != nil {
			return err
		}
		for _, o := range sources {
			if !paidEligible(&o) {
				return d.ErrConflict
			}
		}
		now := time.Now()
		claim := tx.Model(&d.Request{}).Where("id = ? AND status = ?", id, d.StatusProcessing).Updates(map[string]interface{}{"status": d.StatusIssued, "invoice_number": number, "issued_by": admin, "issued_at": now, "updated_at": now})
		if claim.Error != nil {
			return claim.Error
		}
		if claim.RowsAffected != 1 {
			return d.ErrConflict
		}
		for _, o := range sources {
			if err := tx.Model(&od.Order{}).Where("id = ? AND invoice_request_id = ?", o.ID, id).Update("invoice_status", d.StatusIssued).Error; err != nil {
				return err
			}
		}
		result.Status = d.StatusIssued
		result.InvoiceNumber = number
		result.IssuedBy = admin
		result.IssuedAt = &now
		return nil
	})
	return &result, err
}

func (s *RequestStore) Cancel(id, user uint) error {
	if id == 0 || user == 0 {
		return d.ErrInvalid
	}
	return s.db.Transaction(func(tx *gorm.DB) error {
		var r d.Request
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).Where("id = ? AND user_id = ?", id, user).First(&r).Error; err != nil {
			if errors.Is(err, gorm.ErrRecordNotFound) {
				return d.ErrNotFound
			}
			return err
		}
		if r.Status != d.StatusPendingTaxPayment || r.PaymentOrderID == nil {
			return d.ErrConflict
		}
		var payment od.Order
		if err := tx.Clauses(clause.Locking{Strength: "UPDATE"}).First(&payment, *r.PaymentOrderID).Error; err != nil {
			return err
		}
		if payment.PaidAt != nil {
			return d.ErrConflict
		}
		if err := tx.Model(&r).Updates(map[string]interface{}{"status": d.StatusCanceled, "updated_at": time.Now()}).Error; err != nil {
			return err
		}
		if payment.Purpose == "invoice_tax" {
			if err := tx.Model(&od.Order{}).Where("invoice_request_id = ? AND id <> ?", r.ID, payment.ID).Updates(map[string]interface{}{"invoice_requested": false, "invoice_request_id": nil, "invoice_status": "none", "invoice_type": ""}).Error; err != nil {
				return err
			}
		}
		if err := tx.Where("request_id = ?", r.ID).Delete(&d.OrderLink{}).Error; err != nil {
			return err
		}
		return nil
	})
}

// HasPendingSource blocks refund races only while a supplement is unpaid; operators can cancel it first.
func HasPendingSource(tx *gorm.DB, o *od.Order) error {
	if o.InvoiceRequestID == nil || o.Purpose == "invoice_tax" {
		return nil
	}
	var r d.Request
	if err := tx.First(&r, *o.InvoiceRequestID).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil
		}
		return err
	}
	if r.Status == d.StatusPendingTaxPayment && r.PaymentOrderID != nil && *r.PaymentOrderID != o.ID {
		return d.ErrConflict
	}
	return nil
}
