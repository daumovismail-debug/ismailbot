package ws

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHubServeWS(t *testing.T) {
	h := NewHub()
	req := httptest.NewRequest(http.MethodGet, "/v1/ws", nil)
	w := httptest.NewRecorder()
	h.ServeWS(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("expected 200 got %d", w.Code)
	}
}
