package gormstore

import (
	"errors"
	d "github.com/dujiao-next/internal/modules/invoice/domain"
	"gorm.io/gorm"
)

func (s *RequestStore) GetByIDAndUser(id, user uint) (*d.Request, error) {
	if user == 0 {
		return nil, d.ErrInvalid
	}
	var r d.Request
	if err := s.db.Where("id = ? AND user_id = ?", id, user).First(&r).Error; err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, d.ErrNotFound
		}
		return nil, err
	}
	return &r, nil
}
