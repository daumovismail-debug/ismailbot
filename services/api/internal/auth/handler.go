package auth

import (
	"encoding/json"
	"net/http"
	"time"

	"vant2/services/api/internal/store"
)

type Handler struct{ mem *store.Memory }

func NewHandler(mem *store.Memory) *Handler { return &Handler{mem: mem} }

type sendOTPReq struct { Phone string `json:"phone"` }
type verifyOTPReq struct { Phone string `json:"phone"`; Code string `json:"code"` }

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func (h *Handler) SendOTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req sendOTPReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.Phone == "" {
		http.Error(w, "invalid payload", http.StatusBadRequest)
		return
	}
	code := "123456" // TODO: replace with SMS provider
	h.mem.SaveOTP(req.Phone, code, 5*time.Minute)
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "dev_code": code})
}

func (h *Handler) VerifyOTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req verifyOTPReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid payload", http.StatusBadRequest)
		return
	}
	ok := h.mem.VerifyOTP(req.Phone, req.Code)
	if !ok {
		http.Error(w, "invalid code", http.StatusUnauthorized)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "token": BuildDevToken(req.Phone)})
}
