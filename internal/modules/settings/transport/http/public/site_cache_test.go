package publicconfighttp

import (
	"context"
	"encoding/json"
	"net/http/httptest"
	"testing"
	"time"

	reseller "github.com/dujiao-next/internal/modules/reseller/contract"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

type siteCache struct{ key string }

func (s *siteCache) CacheKey(*uint) string { return "public-config:main" }
func (s *siteCache) GetJSON(_ context.Context, key string, dest *map[string]interface{}) (bool, error) {
	s.key = key
	*dest = map[string]interface{}{"tenant": key}
	return true, nil
}
func (s *siteCache) SetJSON(context.Context, string, interface{}, time.Duration) error { return nil }
func TestOperatorSitesNeverShareMainPublicConfigCache(t *testing.T) {
	gin.SetMode(gin.TestMode)
	cache := &siteCache{}
	h := &Handler{cache: cache}
	for _, site := range []struct {
		id         uint
		host, want string
	}{{1, "abc.gptpaynow.com", "public-config:main:site:1:abc.gptpaynow.com"}, {2, "xyz.gptpaynow.com", "public-config:main:site:2:xyz.gptpaynow.com"}, {0, "www.gptpaynow.com", "public-config:main"}} {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "https://"+site.host+"/api/v1/public/config", nil)
		tenant := reseller.MainTenantContext(site.host)
		tenant.SourceSiteID = site.id
		c.Request = req.WithContext(reseller.WithTenantContext(req.Context(), tenant))
		h.GetConfig(c)
		require.Equal(t, site.want, cache.key)
		var result struct {
			Data map[string]interface{} `json:"data"`
		}
		require.NoError(t, json.Unmarshal(w.Body.Bytes(), &result))
		require.Equal(t, site.want, result.Data["tenant"])
	}
}
