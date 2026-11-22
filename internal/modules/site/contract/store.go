package contract

import (
	"time"

	sitedomain "github.com/dujiao-next/internal/modules/site/domain"
)

type Filter struct {
	SiteID          *uint // nil: all, 0: unknown historical data
	From, To        time.Time
	Page, PageSize  int
	Keyword, Status string
}

// UserRow intentionally excludes global spend, wallet, notes, and identities.
type UserRow struct {
	ID                 uint      `json:"id"`
	Email              string    `json:"email"`
	DisplayName        string    `json:"display_name"`
	RegistrationSiteID uint      `json:"registration_site_id"`
	RegistrationDomain string    `json:"registration_domain"`
	CreatedAt          time.Time `json:"created_at"`
}
type OrderItemRow struct {
	Title    interface{} `json:"title"`
	Quantity int         `json:"quantity"`
}
type OrderRow struct {
	ID             uint           `json:"id"`
	OrderNo        string         `json:"order_no"`
	SourceSiteID   uint           `json:"source_site_id"`
	SourceDomain   string         `json:"source_domain"`
	UserID         uint           `json:"user_id"`
	BuyerEmail     string         `json:"buyer_email"`
	Status         string         `json:"status"`
	Currency       string         `json:"currency"`
	TotalAmount    string         `json:"total_amount"`
	RefundedAmount string         `json:"refunded_amount"`
	CreatedAt      time.Time      `json:"created_at"`
	Items          []OrderItemRow `gorm:"-" json:"items"`
}
type CurrencyStats struct {
	Currency          string `json:"currency"`
	Orders            int64  `json:"orders"`
	PaidOrders        int64  `json:"paid_orders"`
	MissingCostOrders int64  `json:"missing_cost_orders"`
	Sales             string `json:"sales"`
	Refunds           string `json:"refunds"`
	NetRevenue        string `json:"net_revenue"`
	Cost              string `json:"cost"`
	PaymentFees       string `json:"payment_fees"`
	Profit            string `json:"profit"`
}
type Overview struct {
	RegisteredUsers int64           `json:"registered_users"`
	BrowserVisits   int64           `json:"browser_visits"`
	ByCurrency      []CurrencyStats `json:"by_currency"`
	Accounting      string          `json:"accounting"`
}

type Store interface {
	FindDomain(string) (*sitedomain.Site, error)
	ListSites() ([]sitedomain.Site, error)
	SaveSite(*sitedomain.Site) error
	GetScope(uint) (sitedomain.Scope, error)
	SetGrants(uint, []sitedomain.Grant) error
	AdminExists(uint) (bool, error)
	DomainInUse(string) (bool, error)
	RecordVisit(sitedomain.Visit) error
	ListUsers(Filter) ([]UserRow, int64, error)
	ListOrders(Filter) ([]OrderRow, int64, error)
	GetOrder(uint, Filter) (*OrderRow, error)
	ListVisits(Filter) ([]sitedomain.Visit, int64, error)
	Overview(Filter) (Overview, error)
}
