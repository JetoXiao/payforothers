package application

import (
	"context"
	userdomain "github.com/dujiao-next/internal/modules/identity/user/domain"
	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
)

// Called only before first INSERT, never on login or account linking.
func applyRegistrationSource(ctx context.Context, user *userdomain.User) {
	if user == nil {
		return
	}
	if tenant, ok := resellercontract.TenantFromContext(ctx); ok && !tenant.Unavailable {
		user.RegistrationSiteID = tenant.SourceSiteID
		user.RegistrationDomain = resellercontract.NormalizeHost(tenant.Host)
	}
}
