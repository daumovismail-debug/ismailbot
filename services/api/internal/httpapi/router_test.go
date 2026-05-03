package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealth(t *testing.T) {
	r := NewRouter()
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", w.Code)
	}
}

func getToken(t *testing.T, r http.Handler) string {
	t.Helper()
	sendBody, _ := json.Marshal(map[string]string{"phone": "+1000"})
	sendReq := httptest.NewRequest(http.MethodPost, "/v1/auth/send-otp", bytes.NewReader(sendBody))
	sendW := httptest.NewRecorder()
	r.ServeHTTP(sendW, sendReq)
	var sendResp map[string]any
	_ = json.Unmarshal(sendW.Body.Bytes(), &sendResp)
	code, _ := sendResp["dev_code"].(string)

	verifyBody, _ := json.Marshal(map[string]string{"phone": "+1000", "code": code})
	verifyReq := httptest.NewRequest(http.MethodPost, "/v1/auth/verify-otp", bytes.NewReader(verifyBody))
	verifyW := httptest.NewRecorder()
	r.ServeHTTP(verifyW, verifyReq)
	if verifyW.Code != http.StatusOK {
		t.Fatalf("verify otp expected 200 got %d", verifyW.Code)
	}
	var verifyResp map[string]any
	_ = json.Unmarshal(verifyW.Body.Bytes(), &verifyResp)
	token, _ := verifyResp["token"].(string)
	if token == "" {
		t.Fatal("expected token")
	}
	return token
}

func TestProtectedRoutesRequireAuth(t *testing.T) {
	r := NewRouter()
	req := httptest.NewRequest(http.MethodGet, "/v1/chats", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401 got %d", w.Code)
	}
}

func TestMessagesFlow(t *testing.T) {
	r := NewRouter()
	token := getToken(t, r)
	body, _ := json.Marshal(map[string]string{"chat_id": "c1", "text": "hello", "sender": "u1"})
	postReq := httptest.NewRequest(http.MethodPost, "/v1/messages", bytes.NewReader(body))
	postReq.Header.Set("Authorization", "Bearer "+token)
	postW := httptest.NewRecorder()
	r.ServeHTTP(postW, postReq)
	if postW.Code != http.StatusOK {
		t.Fatalf("post message expected 200 got %d", postW.Code)
	}

	listReq := httptest.NewRequest(http.MethodGet, "/v1/messages?chat_id=c1", nil)
	listReq.Header.Set("Authorization", "Bearer "+token)
	listW := httptest.NewRecorder()
	r.ServeHTTP(listW, listReq)
	if listW.Code != http.StatusOK {
		t.Fatalf("list messages expected 200 got %d", listW.Code)
	}
}
