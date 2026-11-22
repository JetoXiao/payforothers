package contract

import (
	invoicedomain "github.com/dujiao-next/internal/modules/invoice/domain"
)

type ProfileStore interface {
	ListByUser(userID uint) ([]invoicedomain.Profile, error)
	GetByIDAndUser(id, userID uint) (*invoicedomain.Profile, error)
	CreateProfile(profile *invoicedomain.Profile) error
	Update(profile *invoicedomain.Profile) error
	Delete(id, userID uint) error
}

type RequestStore interface {
	GetByIDAndUser(id, user uint) (*invoicedomain.Request, error)
	ListByUser(userID uint, page, pageSize int) ([]invoicedomain.Request, int64, error)
	Apply(userID, profileID uint, kind string, orderNos []string, preview bool) (*invoicedomain.Request, error)
	ListAdmin(page, pageSize int) ([]invoicedomain.Request, int64, error)
	MarkIssued(id, adminID uint, number string) (*invoicedomain.Request, error)
}
