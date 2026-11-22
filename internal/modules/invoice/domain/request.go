package domain

import (
	"time"

	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/dujiao-next/internal/shared/money"
)

const (
	StatusPendingTaxPayment = "pending_tax_payment"
	StatusProcessing        = "processing"
	StatusIssued            = "issued"
	StatusRejected          = "rejected"
	StatusCanceled          = "canceled"
	StatusReview            = "needs_review"
)

// Request tracks an invoice application and, when needed, its tax supplement order.
type Request struct {
	ID              uint         `gorm:"primarykey" json:"id"`
	UserID          uint         `gorm:"index;not null" json:"user_id"`
	InvoiceType     string       `gorm:"type:varchar(20);not null" json:"invoice_type"`
	Currency        string       `gorm:"type:varchar(8);not null" json:"currency"`
	PaymentOrderNo  string       `gorm:"type:varchar(80)" json:"payment_order_no"`
	IssuedBy        uint         `json:"issued_by,omitempty"`
	OrderIDs        jsonmap.JSON `gorm:"type:json;not null" json:"order_ids"`
	OrderNos        jsonmap.JSON `gorm:"type:json;not null" json:"order_nos"`
	ProfileSnapshot jsonmap.JSON `gorm:"type:json;not null" json:"profile_snapshot"`
	Email           string       `gorm:"type:varchar(320);not null" json:"email"`
	TaxRate         money.Amount `gorm:"type:decimal(6,2);not null;default:0" json:"tax_rate"`
	TaxBaseAmount   money.Amount `gorm:"type:decimal(20,2);not null;default:0" json:"tax_base_amount"`
	TaxAmount       money.Amount `gorm:"type:decimal(20,2);not null;default:0" json:"tax_amount"`
	Status          string       `gorm:"index;not null;default:'pending_tax_payment'" json:"status"`
	PaymentOrderID  *uint        `gorm:"index" json:"payment_order_id,omitempty"`
	InvoiceNumber   string       `gorm:"type:varchar(120);index" json:"invoice_number,omitempty"`
	IssuedAt        *time.Time   `json:"issued_at,omitempty"`
	RejectionReason string       `gorm:"type:text" json:"rejection_reason,omitempty"`
	CreatedAt       time.Time    `gorm:"index" json:"created_at"`
	UpdatedAt       time.Time    `json:"updated_at"`
}

func (Request) TableName() string { return "invoice_requests" }

// A unique source order lock prevents parallel/overlapping applications. Only unpaid cancellation releases it.
type OrderLink struct {
	OrderID   uint `gorm:"primaryKey;autoIncrement:false" json:"order_id"`
	RequestID uint `gorm:"index;not null" json:"request_id"`
}

func (OrderLink) TableName() string { return "invoice_order_links" }
