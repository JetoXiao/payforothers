package application_test

import (
	"testing"

	. "github.com/dujiao-next/internal/modules/order/application"
	orderdomain "github.com/dujiao-next/internal/modules/order/domain"
	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
	"github.com/stretchr/testify/require"
)

func TestSiteOrderSourcePersistsForMemberGuestAndChildren(t *testing.T) {
	for _, guest := range []bool{false, true} {
		t.Run(map[bool]string{false: "member", true: "guest"}[guest], func(t *testing.T) {
			f := newOrderResellerSnapshotFixture(t)
			tenant := resellercontract.MainTenantContext("ABC.GPTPAYNOW.COM.:443")
			tenant.SourceSiteID = 7
			var order *orderdomain.Order
			var err error
			if guest {
				order, err = f.svc.CreateGuestOrder(CreateGuestOrderInput{Email: "guest@site.test", OrderPassword: "guest-pass", Tenant: tenant, Items: []CreateOrderItem{{ProductID: f.product.ID, SKUID: f.sku.ID, Quantity: 1}}})
			} else {
				input := f.createInput(f.buyer.ID)
				input.Tenant = tenant
				order, err = f.svc.CreateOrder(input)
			}
			require.NoError(t, err)
			require.Equal(t, uint(7), order.SourceSiteID)
			require.Equal(t, "abc.gptpaynow.com", order.SourceDomain)
			require.Nil(t, order.ResellerID)
			var stored []orderdomain.Order
			require.NoError(t, f.db.Where("id = ? OR parent_id = ?", order.ID, order.ID).Order("id").Find(&stored).Error)
			require.GreaterOrEqual(t, len(stored), 2)
			for _, row := range stored {
				require.Equal(t, uint(7), row.SourceSiteID)
				require.Equal(t, "abc.gptpaynow.com", row.SourceDomain)
				require.Nil(t, row.ResellerID)
			}
			// The source tag must not create a payment tenant boundary: the
			// existing main-site customer lookup can still open this order.
			main := resellercontract.MainTenantContext("gptpaynow.com")
			var fromMain *orderdomain.Order
			if guest {
				fromMain, err = f.svc.GetOrderByGuestOrderNoForTenant(main, order.OrderNo, "guest@site.test", "guest-pass")
			} else {
				fromMain, err = f.svc.GetOrderByUserOrderNoForTenant(main, order.OrderNo, f.buyer.ID)
			}
			require.NoError(t, err)
			require.Equal(t, order.ID, fromMain.ID)
			require.Equal(t, uint(7), fromMain.SourceSiteID)
		})
	}
}
