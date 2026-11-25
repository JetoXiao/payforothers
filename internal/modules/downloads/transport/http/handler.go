package downloadhttp

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/dujiao-next/internal/cache"
	settingsapp "github.com/dujiao-next/internal/modules/settings/application"
	"github.com/dujiao-next/internal/platform/http/ginutil"
	"github.com/dujiao-next/internal/platform/http/response"
	"github.com/dujiao-next/internal/shared/jsonmap"
	"github.com/gin-gonic/gin"
)

const settingsKey = "site_config"

type Settings interface {
	GetByKey(key string) (jsonmap.JSON, error)
	UpdateWithEffects(key string, value map[string]interface{}) (settingsapp.UpdateResult, error)
}

type Handler struct{ settings Settings }

func NewHandler(settings Settings) *Handler { return &Handler{settings: settings} }

type r2Config struct {
	Endpoint        string `json:"endpoint"`
	Bucket          string `json:"bucket"`
	AccessKeyID     string `json:"access_key_id"`
	SecretAccessKey string `json:"secret_access_key"`
	Prefix          string `json:"prefix"`
	PublicURL       string `json:"public_url"`
}

func RegisterPublicRoutes(public gin.IRoutes, h *Handler) {
	public.GET("/downloads/resources", h.PublicResources)
	public.GET("/downloads/resources/:id", h.Download)
}

func RegisterAdminRoutes(admin gin.IRoutes, h *Handler) {
	admin.GET("/downloads/config", h.GetConfig)
	admin.PUT("/downloads/config", h.UpdateConfig)
	admin.POST("/downloads/test", h.TestConnection)
	admin.GET("/downloads/resources", h.AdminResources)
	admin.POST("/downloads/resources", h.CreateResource)
	admin.PUT("/downloads/resources/:id", h.UpdateResource)
	admin.DELETE("/downloads/resources/:id", h.DeleteResource)
}

func (h *Handler) load() (map[string]interface{}, r2Config, []map[string]interface{}, error) {
	value, err := h.settings.GetByKey(settingsKey)
	if err != nil {
		return nil, r2Config{}, nil, err
	}
	config := map[string]interface{}{}
	for k, v := range value {
		config[k] = v
	}
	downloads, _ := config["downloads"].(map[string]interface{})
	r2 := r2ConfigFrom(downloads["r2"])
	resources := resourceList(downloads["resources"])
	return config, r2, resources, nil
}

func r2ConfigFrom(raw interface{}) r2Config {
	m, _ := raw.(map[string]interface{})
	return r2Config{Endpoint: stringValue(m["endpoint"]), Bucket: stringValue(m["bucket"]), AccessKeyID: stringValue(m["access_key_id"]), SecretAccessKey: stringValue(m["secret_access_key"]), Prefix: stringValue(m["prefix"]), PublicURL: stringValue(m["public_url"])}
}

func resourceList(raw interface{}) []map[string]interface{} {
	items, _ := raw.([]interface{})
	out := make([]map[string]interface{}, 0, len(items))
	for _, item := range items {
		if m, ok := item.(map[string]interface{}); ok {
			out = append(out, m)
		}
	}
	return out
}

func stringValue(v interface{}) string { s, _ := v.(string); return strings.TrimSpace(s) }

func (h *Handler) save(config map[string]interface{}, downloads map[string]interface{}) error {
	config["downloads"] = downloads
	result, err := h.settings.UpdateWithEffects(settingsKey, config)
	if err != nil {
		return err
	}
	if result.HasEffect(settingsapp.EffectInvalidatePublicConfigCache) {
		_ = cache.DelAllPublicConfig(context.Background())
	}
	return nil
}

func (h *Handler) GetConfig(c *gin.Context) {
	config, r2, resources, err := h.load()
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_fetch_failed", err)
		return
	}
	_ = config
	r2.SecretAccessKey = ""
	response.Success(c, gin.H{"r2": gin.H{
		"endpoint": r2.Endpoint, "bucket": r2.Bucket, "access_key_id": r2.AccessKeyID,
		"secret_access_key": "", "secret_saved": r2.SecretAccessKey != "", "prefix": r2.Prefix, "public_url": r2.PublicURL,
	}, "resources": resources})
}

func (h *Handler) UpdateConfig(c *gin.Context) {
	var req struct {
		R2 r2Config `json:"r2"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ginutil.RespondBindError(c, err)
		return
	}
	config, old, resources, err := h.load()
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_fetch_failed", err)
		return
	}
	if req.R2.SecretAccessKey == "" {
		req.R2.SecretAccessKey = old.SecretAccessKey
	}
	downloads := map[string]interface{}{"enabled": true, "manifest_url": req.R2.PublicURL + "/manifest.json", "public_url": strings.TrimRight(req.R2.PublicURL, "/"), "r2": structMap(req.R2), "resources": resources}
	if err := h.save(config, downloads); err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_save_failed", err)
		return
	}
	req.R2.SecretAccessKey = ""
	response.Success(c, gin.H{"r2": req.R2, "resources": resources})
}

func (h *Handler) TestConnection(c *gin.Context) {
	var cfg r2Config
	if err := c.ShouldBindJSON(&cfg); err != nil {
		ginutil.RespondBindError(c, err)
		return
	}
	if cfg.SecretAccessKey == "" {
		_, saved, _, loadErr := h.load()
		if loadErr == nil {
			cfg.SecretAccessKey = saved.SecretAccessKey
		}
	}
	if err := validateR2(cfg); err != nil {
		ginutil.RespondErrorWithMsg(c, response.CodeBadRequest, err.Error(), nil)
		return
	}
	status, err := signedRequest("HEAD", cfg, "", nil, "")
	if err != nil || status < 200 || status >= 300 {
		ginutil.RespondErrorWithMsg(c, response.CodeBadRequest, "R2 连接测试失败", err)
		return
	}
	response.Success(c, gin.H{"ok": true})
}

func (h *Handler) AdminResources(c *gin.Context) {
	_, _, resources, err := h.load()
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_fetch_failed", err)
		return
	}
	response.Success(c, resources)
}

func (h *Handler) CreateResource(c *gin.Context) { h.writeResource(c, 0) }
func (h *Handler) UpdateResource(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil || id == 0 {
		ginutil.RespondError(c, response.CodeBadRequest, "error.invalid_id", nil)
		return
	}
	h.writeResource(c, uint(id))
}

func (h *Handler) writeResource(c *gin.Context, id uint) {
	config, cfg, resources, err := h.load()
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_fetch_failed", err)
		return
	}
	var raw map[string]interface{}
	if value := c.PostForm("resource"); value != "" {
		_ = json.Unmarshal([]byte(value), &raw)
	}
	if raw == nil {
		raw = map[string]interface{}{}
	}
	if id == 0 {
		id = uint(time.Now().UnixNano() / 1e6)
	}
	file, fileErr := c.FormFile("file")
	if fileErr == nil {
		key := strings.TrimPrefix(cfg.Prefix, "/") + strings.TrimPrefix(c.PostForm("file_key"), "/")
		if strings.TrimSpace(c.PostForm("file_key")) == "" {
			key = strings.TrimSuffix(cfg.Prefix, "/") + "/" + file.Filename
		}
		data, readErr := readMultipart(file)
		if readErr != nil {
			ginutil.RespondError(c, response.CodeBadRequest, "error.upload_failed", readErr)
			return
		}
		status, putErr := signedRequest("PUT", cfg, key, data, file.Header.Get("Content-Type"))
		if putErr != nil || status < 200 || status >= 300 {
			ginutil.RespondErrorWithMsg(c, response.CodeBadRequest, "R2 上传失败", putErr)
			return
		}
		raw["file_key"] = key
		raw["size"] = formatSize(int64(len(data)))
		raw["sha256"] = sha256Hex(data)
		raw["content_type"] = file.Header.Get("Content-Type")
		raw["download_name"] = file.Filename
	}
	raw["id"] = id
	if raw["download_count"] == nil {
		raw["download_count"] = 0
	}
	if raw["updated_at"] == nil {
		raw["updated_at"] = time.Now().UTC().Format(time.RFC3339)
	}
	updated := false
	for i, item := range resources {
		if number(item["id"]) == id {
			resources[i] = raw
			updated = true
			break
		}
	}
	if !updated {
		resources = append(resources, raw)
	}
	downloads := map[string]interface{}{"enabled": true, "manifest_url": cfg.PublicURL + "/manifest.json", "public_url": strings.TrimRight(cfg.PublicURL, "/"), "r2": structMap(cfg), "resources": resources}
	if err := h.save(config, downloads); err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_save_failed", err)
		return
	}
	response.Success(c, raw)
}

func (h *Handler) DeleteResource(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil || id == 0 {
		ginutil.RespondError(c, response.CodeBadRequest, "error.invalid_id", nil)
		return
	}
	config, cfg, resources, err := h.load()
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_fetch_failed", err)
		return
	}
	filtered := make([]map[string]interface{}, 0, len(resources))
	for _, item := range resources {
		if number(item["id"]) != uint(id) {
			filtered = append(filtered, item)
		}
	}
	downloads := map[string]interface{}{"enabled": true, "manifest_url": cfg.PublicURL + "/manifest.json", "public_url": strings.TrimRight(cfg.PublicURL, "/"), "r2": structMap(cfg), "resources": filtered}
	if err := h.save(config, downloads); err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.settings_save_failed", err)
		return
	}
	response.Success(c, nil)
}

func (h *Handler) PublicResources(c *gin.Context) {
	_, _, resources, err := h.load()
	if err != nil {
		ginutil.RespondError(c, response.CodeInternal, "error.config_fetch_failed", err)
		return
	}
	public := make([]map[string]interface{}, 0, len(resources))
	for _, item := range resources {
		if published, _ := item["published"].(bool); published {
			copy := clone(item)
			id := number(item["id"])
			copy["url"] = "/api/v1/public/downloads/resources/" + strconv.FormatUint(uint64(id), 10)
			public = append(public, copy)
		}
	}
	response.Success(c, gin.H{"resources": public})
}

func (h *Handler) Download(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil || id == 0 {
		c.Status(http.StatusNotFound)
		return
	}
	config, cfg, resources, err := h.load()
	if err != nil {
		c.Status(http.StatusInternalServerError)
		return
	}
	for _, item := range resources {
		if number(item["id"]) == uint(id) {
			published, _ := item["published"].(bool)
			if !published {
				c.Status(http.StatusNotFound)
				return
			}
			key := stringValue(item["file_key"])
			_, err = signedRequest("GET", cfg, key, nil, "")
			if err != nil {
				c.Status(http.StatusBadGateway)
				return
			}
			item["download_count"] = number(item["download_count"]) + 1
			downloads := map[string]interface{}{"enabled": true, "manifest_url": cfg.PublicURL + "/manifest.json", "public_url": strings.TrimRight(cfg.PublicURL, "/"), "r2": structMap(cfg), "resources": resources}
			_ = h.save(config, downloads)
			c.Redirect(http.StatusFound, signedURL(cfg, key, 15*time.Minute))
			return
		}
	}
	c.Status(http.StatusNotFound)
}

func validateR2(cfg r2Config) error {
	if cfg.Endpoint == "" || cfg.Bucket == "" || cfg.AccessKeyID == "" || cfg.SecretAccessKey == "" {
		return fmt.Errorf("R2 配置不完整")
	}
	return nil
}
func structMap(cfg r2Config) map[string]interface{} {
	return map[string]interface{}{"endpoint": cfg.Endpoint, "bucket": cfg.Bucket, "access_key_id": cfg.AccessKeyID, "secret_access_key": cfg.SecretAccessKey, "prefix": cfg.Prefix, "public_url": cfg.PublicURL}
}
func clone(v map[string]interface{}) map[string]interface{} {
	out := map[string]interface{}{}
	for k, x := range v {
		out[k] = x
	}
	return out
}
func number(v interface{}) uint {
	switch n := v.(type) {
	case float64:
		return uint(n)
	case int:
		return uint(n)
	case uint:
		return n
	case json.Number:
		x, _ := strconv.ParseUint(string(n), 10, 64)
		return uint(x)
	default:
		x, _ := strconv.ParseUint(stringValue(v), 10, 64)
		return uint(x)
	}
}
func readMultipart(file *multipart.FileHeader) ([]byte, error) {
	if file.Size > 1024*1024*1024 {
		return nil, fmt.Errorf("文件超过 1GB 限制")
	}
	f, err := file.Open()
	if err != nil {
		return nil, err
	}
	defer f.Close()
	return io.ReadAll(io.LimitReader(f, 1024*1024*1024+1))
}
func formatSize(n int64) string {
	units := []string{"B", "KB", "MB", "GB"}
	size := float64(n)
	i := 0
	for size >= 1024 && i < len(units)-1 {
		size /= 1024
		i++
	}
	return fmt.Sprintf("%.2f %s", size, units[i])
}
func sha256Hex(data []byte) string { sum := sha256.Sum256(data); return hex.EncodeToString(sum[:]) }

func signedURL(cfg r2Config, key string, ttl time.Duration) string { return signURL(cfg, key, ttl) }
func signURL(cfg r2Config, key string, ttl time.Duration) string {
	u, _ := url.Parse(strings.TrimRight(cfg.Endpoint, "/"))
	u.Path = "/" + strings.Trim(cfg.Bucket, "/") + "/" + strings.TrimLeft(key, "/")
	now := time.Now().UTC()
	scope := now.Format("20060102") + "/auto/s3/aws4_request"
	credential := cfg.AccessKeyID + "/" + scope
	params := u.Query()
	params.Set("X-Amz-Algorithm", "AWS4-HMAC-SHA256")
	params.Set("X-Amz-Credential", credential)
	params.Set("X-Amz-Date", now.Format("20060102T150405Z"))
	params.Set("X-Amz-Expires", strconv.FormatInt(int64(ttl.Seconds()), 10))
	params.Set("X-Amz-SignedHeaders", "host")
	u.RawQuery = params.Encode()
	canonical := "GET\n" + uriPath(u.Path) + "\n" + canonicalQuery(u.Query()) + "\nhost:" + u.Host + "\n\nhost\nUNSIGNED-PAYLOAD"
	signature := signature(cfg.SecretAccessKey, now, scope, canonical)
	params.Set("X-Amz-Signature", signature)
	u.RawQuery = params.Encode()
	return u.String()
}
func signedRequest(method string, cfg r2Config, key string, body []byte, contentType string) (int, error) {
	reqURL, _ := url.Parse(strings.TrimRight(cfg.Endpoint, "/"))
	reqURL.Path = "/" + strings.Trim(cfg.Bucket, "/") + "/" + strings.TrimLeft(key, "/")
	req, err := http.NewRequest(method, reqURL.String(), bytes.NewReader(body))
	if err != nil {
		return 0, err
	}
	req.Header.Set("Host", reqURL.Host)
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	now := time.Now().UTC()
	scope := now.Format("20060102") + "/auto/s3/aws4_request"
	payload := sha256Hex(body)
	canonical := method + "\n" + uriPath(reqURL.Path) + "\n\n" + "host:" + reqURL.Host + "\n" + "x-amz-content-sha256:" + payload + "\n\n" + "host;x-amz-content-sha256\n" + payload
	req.Header.Set("x-amz-content-sha256", payload)
	req.Header.Set("x-amz-date", now.Format("20060102T150405Z"))
	sig := signature(cfg.SecretAccessKey, now, scope, canonical)
	req.Header.Set("Authorization", "AWS4-HMAC-SHA256 Credential="+cfg.AccessKeyID+"/"+scope+", SignedHeaders=host;x-amz-content-sha256, Signature="+sig)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	return resp.StatusCode, nil
}
func signature(secret string, now time.Time, scope, canonical string) string {
	date := now.Format("20060102")
	kDate := hmacSHA([]byte("AWS4"+secret), date)
	kRegion := hmacSHA(kDate, "auto")
	kService := hmacSHA(kRegion, "s3")
	kSigning := hmacSHA(kService, "aws4_request")
	hashed := sha256Hex([]byte(canonical))
	stringToSign := "AWS4-HMAC-SHA256\n" + now.Format("20060102T150405Z") + "\n" + scope + "\n" + hashed
	return hex.EncodeToString(hmacSHA(kSigning, stringToSign))
}
func hmacSHA(key []byte, data string) []byte {
	h := hmac.New(sha256.New, key)
	_, _ = h.Write([]byte(data))
	return h.Sum(nil)
}
func uriPath(v string) string { return strings.ReplaceAll(url.PathEscape(v), "+", "%20") }
func canonicalQuery(q url.Values) string {
	keys := make([]string, 0, len(q))
	for k := range q {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := []string{}
	for _, k := range keys {
		values := q[k]
		sort.Strings(values)
		for _, v := range values {
			parts = append(parts, url.QueryEscape(k)+"="+url.QueryEscape(v))
		}
	}
	return strings.Join(parts, "&")
}
