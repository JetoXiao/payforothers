package contract

import (
	productcatalog "github.com/dujiao-next/internal/modules/productcatalog/domain"
)

type Filter struct {
	Page, PageSize int
	Search         string
	ProductActive  *bool
	FollowPrice    *bool
}
type Store interface {
	List(Filter) ([]productcatalog.Item, int64, error)
	Sync(bool) (int, error)
	Update(uint, map[string]interface{}) (*productcatalog.Item, error)
}
