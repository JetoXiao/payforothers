package domain

import "time"

// Profile stores the legally required billing identity supplied by a user.
type Profile struct {
	ID          uint       `gorm:"primarykey" json:"id"`
	UserID      uint       `gorm:"index;not null" json:"user_id"`
	Name        string     `gorm:"type:varchar(200);not null" json:"name"`
	Type        string     `gorm:"type:varchar(20);not null;default:'company'" json:"type"`
	TaxpayerID  string     `gorm:"type:varchar(100);not null" json:"taxpayer_id"`
	Address     string     `gorm:"type:varchar(500);not null" json:"address"`
	Phone       string     `gorm:"type:varchar(80);not null" json:"phone"`
	BankName    string     `gorm:"type:varchar(200);not null" json:"bank_name"`
	BankAccount string     `gorm:"type:varchar(100);not null" json:"bank_account"`
	Email       string     `gorm:"type:varchar(320);not null" json:"email"`
	IsDefault   bool       `gorm:"not null;default:false" json:"is_default"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	DeletedAt   *time.Time `gorm:"index" json:"-"`
}

func (Profile) TableName() string { return "invoice_profiles" }
