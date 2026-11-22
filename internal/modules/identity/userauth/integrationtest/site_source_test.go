package integrationtest

import (
	"context"
	"testing"
	"time"

	"github.com/dujiao-next/internal/config"
	telegramauthapp "github.com/dujiao-next/internal/modules/identity/telegramauth/application"
	userdomain "github.com/dujiao-next/internal/modules/identity/user/domain"
	userstore "github.com/dujiao-next/internal/modules/identity/user/infrastructure/gormstore"
	userauthapp "github.com/dujiao-next/internal/modules/identity/userauth/application"
	userauthstore "github.com/dujiao-next/internal/modules/identity/userauth/infrastructure/gormstore"
	resellercontract "github.com/dujiao-next/internal/modules/reseller/contract"
	"github.com/stretchr/testify/require"
)

func siteContext(id uint, host string) context.Context {
	tenant := resellercontract.MainTenantContext(host)
	tenant.SourceSiteID = id
	return resellercontract.WithTenantContext(context.Background(), tenant)
}
func TestEmailRegistrationSourceIsImmutableAcrossLogins(t *testing.T) {
	svc, _, db := setupTelegramOAuthTestService(t)
	user, _, _, err := svc.RegisterWithContext(siteContext(7, "abc.gptpaynow.com"), "site@example.test", "test-password-123", "", true, false)
	require.NoError(t, err)
	require.Equal(t, uint(7), user.RegistrationSiteID)
	require.Equal(t, "abc.gptpaynow.com", user.RegistrationDomain)
	_, err = svc.LoginStep1("site@example.test", "test-password-123", false)
	require.NoError(t, err)
	var stored userdomain.User
	require.NoError(t, db.First(&stored, user.ID).Error)
	require.Equal(t, uint(7), stored.RegistrationSiteID)
}
func TestTelegramRegistrationUsesRequestSiteAndDoesNotReattributeExistingUser(t *testing.T) {
	botToken := "site-test-bot-token"
	verifier := telegramauthapp.NewService(config.TelegramAuthConfig{Enabled: true, BotToken: botToken, LoginExpireSeconds: 300, ReplayTTLSeconds: 300}, telegramauthapp.WithReplaySetNX(func(context.Context, string, interface{}, time.Duration) (bool, error) { return true, nil }))
	svc, _, db := setupTelegramOAuthTestService(t, verifier)
	initData := buildUserAuthTestTelegramMiniAppInitData(t, botToken, time.Now().Unix(), `{"id":777001,"first_name":"Site Buyer"}`)
	result, err := svc.LoginWithTelegramMiniApp(userauthapp.LoginWithTelegramMiniAppInput{InitData: initData, Context: siteContext(7, "abc.gptpaynow.com")})
	require.NoError(t, err)
	require.Equal(t, uint(7), result.User.RegistrationSiteID)
	result, err = svc.LoginWithTelegramMiniApp(userauthapp.LoginWithTelegramMiniAppInput{InitData: initData, Context: siteContext(8, "xyz.gptpaynow.com")})
	require.NoError(t, err)
	var stored userdomain.User
	require.NoError(t, db.First(&stored, result.User.ID).Error)
	require.Equal(t, uint(7), stored.RegistrationSiteID)
	require.Equal(t, "abc.gptpaynow.com", stored.RegistrationDomain)
}

func TestGoogleRegistrationSourcePersistsAndExistingIdentityKeepsIt(t *testing.T) {
	svc, _, db := setupTelegramOAuthTestService(t)
	identity := verifiedGoogleIdentity("site-google@gmail.com", "site-google-sub", true)
	result, err := svc.LoginVerifiedGoogleWithContext(siteContext(7, "abc.gptpaynow.com"), identity)
	require.NoError(t, err)
	require.Equal(t, uint(7), result.User.RegistrationSiteID)
	result, err = svc.LoginVerifiedGoogleWithContext(siteContext(8, "xyz.gptpaynow.com"), identity)
	require.NoError(t, err)
	var stored userdomain.User
	require.NoError(t, db.First(&stored, result.User.ID).Error)
	require.Equal(t, uint(7), stored.RegistrationSiteID)
	require.Equal(t, "abc.gptpaynow.com", stored.RegistrationDomain)
}

func TestProfileUpdatesCannotOverwriteRegistrationAttribution(t *testing.T) {
	_, _, db := setupTelegramOAuthTestService(t)
	user := &userdomain.User{Email: "source-immutable@example.test", PasswordHash: "hash", RegistrationSiteID: 7, RegistrationDomain: "abc.gptpaynow.com"}
	require.NoError(t, db.Create(user).Error)
	user.RegistrationSiteID = 8
	user.RegistrationDomain = "xyz.gptpaynow.com"
	user.DisplayName = "Updated"
	require.NoError(t, userstore.New(db).Update(user))
	var stored userdomain.User
	require.NoError(t, db.First(&stored, user.ID).Error)
	require.Equal(t, uint(7), stored.RegistrationSiteID)
	require.Equal(t, "Updated", stored.DisplayName)
	require.NoError(t, userauthstore.New(db).WithinTransaction(context.Background(), func(tx userauthapp.AuthTransaction) error { return tx.UpdateUser(user) }))
	require.NoError(t, db.First(&stored, user.ID).Error)
	require.Equal(t, uint(7), stored.RegistrationSiteID)
	require.Equal(t, "abc.gptpaynow.com", stored.RegistrationDomain)
}
