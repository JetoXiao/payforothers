package wecom

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
	"unicode/utf8"
)

const testHook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=0123456789abcdef"

type roundTrip func(*http.Request) (*http.Response, error)

func (r roundTrip) RoundTrip(req *http.Request) (*http.Response, error) { return r(req) }

func senderForTest(handler roundTrip) *Sender {
	s := New()
	s.client.Transport = handler
	state := map[string]string{}
	s.get = func(_ context.Context, k string) (string, error) { return state[k], nil }
	s.set = func(_ context.Context, k, v string, _ time.Duration) error { state[k] = v; return nil }
	s.lock = func(_ context.Context, k string, _ interface{}, _ time.Duration) (bool, error) {
		if strings.HasSuffix(k, ":rate") {
			return true, nil
		}
		if state[k] != "" {
			return false, nil
		}
		state[k] = "1"
		return true, nil
	}
	s.del = func(_ context.Context, k string) error { delete(state, k); return nil }
	return s
}
func response(status int, body string) *http.Response {
	return &http.Response{StatusCode: status, Header: make(http.Header), Body: io.NopCloser(strings.NewReader(body))}
}

func TestRetryAndDedupe(t *testing.T) {
	calls := 0
	s := senderForTest(func(r *http.Request) (*http.Response, error) {
		calls++
		var body struct {
			Type string `json:"msgtype"`
			Text struct {
				Content string `json:"content"`
			} `json:"text"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Fatal(err)
		}
		if body.Type != "text" || len(body.Text.Content) > 2048 || !utf8.ValidString(body.Text.Content) {
			t.Fatal("invalid UTF-8 payload")
		}
		if calls == 1 {
			return response(200, `{"errcode":45009,"errmsg":"secret"}`), nil
		}
		return response(200, `{"errcode":0}`), nil
	})
	ctx := context.Background()
	if s.SendMessage(ctx, testHook, "order:1", strings.Repeat("你好", 800)) == nil {
		t.Fatal("expected rejection")
	}
	if err := s.SendMessage(ctx, testHook, "order:1", "retry"); err != nil {
		t.Fatal(err)
	}
	if err := s.SendMessage(ctx, testHook, "order:1", "duplicate"); err != nil {
		t.Fatal(err)
	}
	if calls != 2 {
		t.Fatalf("calls=%d", calls)
	}
}

func TestFailuresAreRedactedAndNotAccepted(t *testing.T) {
	for _, tc := range []struct {
		status int
		body   string
		err    error
	}{
		{500, "", nil}, {200, `{}`, nil}, {200, `{"errcode":1,"errmsg":"` + testHook + `"}`, nil}, {200, "not-json", nil}, {200, strings.Repeat("x", 8193), nil}, {0, "", errors.New(testHook)},
	} {
		s := senderForTest(func(*http.Request) (*http.Response, error) {
			if tc.err != nil {
				return nil, tc.err
			}
			return response(tc.status, tc.body), nil
		})
		err := s.SendMessage(context.Background(), testHook, "order:2", "text")
		if err == nil || strings.Contains(err.Error(), "0123456789abcdef") {
			t.Fatal("failure leaked or accepted", err)
		}
	}
}

func TestRedirectBlocked(t *testing.T) {
	calls := 0
	s := senderForTest(func(*http.Request) (*http.Response, error) {
		calls++
		r := response(302, "")
		r.Header.Set("Location", "https://example.com")
		return r, nil
	})
	if s.SendMessage(context.Background(), testHook, "", "test") == nil || calls != 1 {
		t.Fatal("redirect not blocked")
	}
}

func TestRateLimitAndBusyRetryable(t *testing.T) {
	s := senderForTest(func(*http.Request) (*http.Response, error) { t.Fatal("must not send"); return nil, nil })
	s.lock = func(context.Context, string, interface{}, time.Duration) (bool, error) { return false, nil }
	for _, key := range []string{"", "order:3"} {
		if s.SendMessage(context.Background(), testHook, key, "text") == nil {
			t.Fatal("must retry")
		}
	}
}
