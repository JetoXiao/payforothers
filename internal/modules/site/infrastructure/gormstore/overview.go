package gormstore

import (
	"github.com/dujiao-next/internal/constants"
	userdomain "github.com/dujiao-next/internal/modules/identity/user/domain"
	sitecontract "github.com/dujiao-next/internal/modules/site/contract"
	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
	"github.com/shopspring/decimal"
)

// Financial values are decimal strings; each main order is counted once.
func (s *Store) Overview(f sitecontract.Filter) (sitecontract.Overview, error) {
	out := sitecontract.Overview{ByCurrency: []sitecontract.CurrencyStats{}, Accounting: "Order-created cohort; net of refunds and invoice tax; snapshot cost is not reversed on refunds; excludes overhead and marketing. Zero costs may overstate gross profit."}
	if err := window(siteQuery(s.db.Model(&userdomain.User{}).Where("deleted_at IS NULL"), "registration_site_id", f), "created_at", f).Count(&out.RegisteredUsers).Error; err != nil {
		return out, err
	}
	visits := window(siteQuery(s.db.Model(&sitedomain.Visit{}), "site_id", f), "first_seen_at", f).Select("site_id,day,visitor_hash").Group("site_id,day,visitor_hash")
	if err := s.db.Table("(?) AS browsers", visits).Count(&out.BrowserVisits).Error; err != nil {
		return out, err
	}
	var counts []struct {
		Currency string
		Orders   int64
	}
	if err := s.orderQuery(f).Select("orders.currency,COUNT(*) AS orders").Group("orders.currency").Scan(&counts).Error; err != nil {
		return out, err
	}
	statuses := []string{constants.OrderStatusPaid, constants.OrderStatusFulfilling, constants.OrderStatusPartiallyDelivered, constants.OrderStatusPartiallyRefunded, constants.OrderStatusDelivered, constants.OrderStatusCompleted, constants.OrderStatusRefunded}
	for _, c := range counts {
		q := s.orderQuery(f).Where("orders.currency = ? AND (orders.paid_at IS NOT NULL OR orders.status IN ?)", c.Currency, statuses)
		var row struct {
			PaidOrders          int64
			Sales, Refunds, Tax decimal.Decimal
			Cost                decimal.Decimal
			MissingCostOrders   int64
		}
		// The correlated item aggregate prevents a main order from multiplying with its children.
		err := q.Select(`COUNT(*) AS paid_orders, COALESCE(SUM(orders.total_amount),0) AS sales,
		COALESCE(SUM(orders.refunded_amount),0) AS refunds,
		COALESCE(SUM(CASE WHEN orders.total_amount > 0 THEN orders.invoice_tax_amount * (1.0-1.0*orders.refunded_amount/orders.total_amount) ELSE 0 END),0) AS tax,
		COALESCE(SUM((SELECT COALESCE(SUM(i.cost_price*i.quantity),0) FROM order_items i JOIN orders child ON child.id=i.order_id WHERE i.deleted_at IS NULL AND child.deleted_at IS NULL AND (child.id=orders.id OR child.parent_id=orders.id))),0) AS cost,
		COALESCE(SUM(CASE WHEN EXISTS(SELECT 1 FROM order_items i JOIN orders child ON child.id=i.order_id WHERE i.deleted_at IS NULL AND child.deleted_at IS NULL AND (child.id=orders.id OR child.parent_id=orders.id) AND i.cost_price=0) THEN 1 ELSE 0 END),0) AS missing_cost_orders`).Scan(&row).Error
		if err != nil {
			return out, err
		}
		var fees decimal.Decimal
		ids := s.orderQuery(f).Select("orders.id").Where("orders.currency = ?", c.Currency)
		if err := s.db.Table("payments").Select("COALESCE(SUM(fee_amount),0)").Where("deleted_at IS NULL AND order_id IN (?) AND currency = ? AND status = ? AND provider_type <> ? AND fee_policy = ?", ids, c.Currency, constants.PaymentStatusSuccess, constants.PaymentProviderWallet, constants.PaymentFeePolicyMerchantAbsorbed).Scan(&fees).Error; err != nil {
			return out, err
		}
		var returnedFees decimal.Decimal
		// Refund records belong either to the root or to one of its children.
		if err := s.db.Table("order_refund_records r").Select("COALESCE(SUM(r.payment_fee_refunded_amount),0)").Joins("JOIN orders o ON o.id=r.order_id").Where("r.deleted_at IS NULL AND o.deleted_at IS NULL AND (o.id IN (?) OR o.parent_id IN (?)) AND r.currency = ?", ids, ids, c.Currency).Scan(&returnedFees).Error; err != nil {
			return out, err
		}
		fees = fees.Sub(returnedFees)
		net := row.Sales.Sub(row.Refunds).Sub(row.Tax)
		out.ByCurrency = append(out.ByCurrency, sitecontract.CurrencyStats{Currency: c.Currency, Orders: c.Orders, PaidOrders: row.PaidOrders, MissingCostOrders: row.MissingCostOrders, Sales: row.Sales.StringFixed(2), Refunds: row.Refunds.StringFixed(2), NetRevenue: net.StringFixed(2), Cost: row.Cost.StringFixed(2), PaymentFees: fees.StringFixed(2), Profit: net.Sub(row.Cost).Sub(fees).StringFixed(2)})
	}
	return out, nil
}
