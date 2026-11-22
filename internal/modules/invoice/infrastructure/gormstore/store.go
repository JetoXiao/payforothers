package gormstore

import (
	"errors"
	"time"

	invoicecontract "github.com/dujiao-next/internal/modules/invoice/contract"
	invoicedomain "github.com/dujiao-next/internal/modules/invoice/domain"
	"gorm.io/gorm"
)

var _ invoicecontract.ProfileStore = (*ProfileStore)(nil)
var _ invoicecontract.RequestStore = (*RequestStore)(nil)

type ProfileStore struct{ db *gorm.DB }
type RequestStore struct{ db *gorm.DB }

func New(db *gorm.DB) *ProfileStore             { return &ProfileStore{db: db} }
func NewRequestStore(db *gorm.DB) *RequestStore { return &RequestStore{db: db} }

func (s *ProfileStore) ListByUser(userID uint) ([]invoicedomain.Profile, error) {
	rows := []invoicedomain.Profile{}
	err := s.db.Where("user_id = ? AND deleted_at IS NULL", userID).Order("is_default DESC, id DESC").Find(&rows).Error
	return rows, err
}
func (s *ProfileStore) GetByIDAndUser(id, userID uint) (*invoicedomain.Profile, error) {
	var row invoicedomain.Profile
	err := s.db.Where("id = ? AND user_id = ? AND deleted_at IS NULL", id, userID).First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return nil, nil
	}
	return &row, err
}
func (s *ProfileStore) CreateProfile(profile *invoicedomain.Profile) error {
	return s.db.Transaction(func(tx *gorm.DB) error {
		if profile.IsDefault {
			if err := tx.Model(&invoicedomain.Profile{}).Where("user_id = ? AND deleted_at IS NULL", profile.UserID).Update("is_default", false).Error; err != nil {
				return err
			}
		}
		return tx.Create(profile).Error
	})
}
func (s *ProfileStore) Update(profile *invoicedomain.Profile) error {
	return s.db.Transaction(func(tx *gorm.DB) error {
		if profile.IsDefault {
			if err := tx.Model(&invoicedomain.Profile{}).Where("user_id = ? AND id <> ? AND deleted_at IS NULL", profile.UserID, profile.ID).Update("is_default", false).Error; err != nil {
				return err
			}
		}
		return tx.Model(&invoicedomain.Profile{}).Where("id = ? AND user_id = ? AND deleted_at IS NULL", profile.ID, profile.UserID).Select("name", "type", "taxpayer_id", "address", "phone", "bank_name", "bank_account", "email", "is_default", "updated_at").Updates(profile).Error
	})
}
func (s *ProfileStore) Delete(id, userID uint) error {
	return s.db.Model(&invoicedomain.Profile{}).Where("id = ? AND user_id = ? AND deleted_at IS NULL", id, userID).Update("deleted_at", time.Now()).Error
}
