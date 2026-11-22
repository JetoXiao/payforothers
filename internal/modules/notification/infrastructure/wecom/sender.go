package wecom

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"
	"unicode/utf8"

	"github.com/dujiao-next/internal/cache"
	settingsmessaging "github.com/dujiao-next/internal/modules/settings/schema/messaging"
)

type Sender struct {
	client *http.Client
	get    func(context.Context, string) (string, error)
	set    func(context.Context, string, string, time.Duration) error
	lock   func(context.Context, string, interface{}, time.Duration) (bool, error)
	del    func(context.Context, string) error
}

func New() *Sender {
	return &Sender{client: &http.Client{Timeout: 10 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}, get: cache.GetString, set: cache.SetString, lock: cache.SetNX, del: cache.Del}
}

// SendMessage marks delivery only after an accepted response, so queue retries
// survive failures. The URL/key is never included in returned errors or logs.
func (s *Sender) SendMessage(ctx context.Context, webhook, eventKey, message string) error {
	if err := settingsmessaging.ValidateWeComWebhook(webhook); err != nil {
		return err
	}
	bot := fmt.Sprintf("notification:wecom:%x", sha256.Sum256([]byte(webhook)))
	if eventKey != "" {
		key := fmt.Sprintf("%s:sent:%x", bot, sha256.Sum256([]byte(eventKey)))
		sent, err := s.get(ctx, key)
		if err != nil {
			return errors.New("wecom delivery state unavailable")
		}
		if sent != "" {
			return nil
		}
		ok, err := s.lock(ctx, key+":lock", "1", 30*time.Second)
		if err != nil || !ok {
			return errors.New("wecom delivery busy; retry later")
		}
		defer func() {
			cleanup, cancel := context.WithTimeout(context.WithoutCancel(ctx), 3*time.Second)
			defer cancel()
			_ = s.del(cleanup, key+":lock")
		}()
		// A concurrent worker may have delivered between GET and acquiring the lock.
		sent, err = s.get(ctx, key)
		if err != nil {
			return errors.New("wecom delivery state unavailable")
		}
		if sent != "" {
			return nil
		}
		if err := s.send(ctx, webhook, bot, message); err != nil {
			return err
		}
		if err := s.set(ctx, key, "1", 30*24*time.Hour); err != nil {
			return errors.New("wecom delivery receipt storage failed")
		}
		return nil
	}
	return s.send(ctx, webhook, bot, message)
}

func (s *Sender) send(ctx context.Context, webhook, bot, message string) error {
	// Tencent limits each bot to 20 messages/minute. Retries use the same limiter.
	ok, err := s.lock(ctx, bot+":rate", "1", 3100*time.Millisecond)
	if err != nil || !ok {
		return errors.New("wecom rate limited; retry later")
	}
	message = truncateText(message, 2048)
	body, _ := json.Marshal(map[string]interface{}{"msgtype": "text", "text": map[string]string{"content": message}})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, webhook, bytes.NewReader(body))
	if err != nil {
		return errors.New("wecom request invalid")
	}
	req.Header.Set("Content-Type", "application/json; charset=utf-8")
	resp, err := s.client.Do(req)
	if err != nil {
		return errors.New("wecom network request failed")
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("wecom HTTP status %d", resp.StatusCode)
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, 8193))
	if err != nil || len(data) > 8192 {
		return errors.New("wecom response invalid")
	}
	var result struct {
		Code *int `json:"errcode"`
	}
	if json.Unmarshal(data, &result) != nil || result.Code == nil {
		return errors.New("wecom response invalid")
	}
	if *result.Code != 0 {
		return fmt.Errorf("wecom rejected message (code %d)", *result.Code)
	}
	return nil
}

func truncateText(text string, limit int) string {
	if len(text) <= limit {
		return text
	}
	text = text[:limit-len("\n…")]
	for !utf8.ValidString(text) {
		text = text[:len(text)-1]
	}
	return text + "\n…"
}
