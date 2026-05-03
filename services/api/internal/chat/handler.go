package chat

import (
	"encoding/json"
	"net/http"
	"time"

	"vant2/services/api/internal/store"
)

type Handler struct{ mem *store.Memory }

func NewHandler(mem *store.Memory) *Handler { return &Handler{mem: mem} }

type postMessageReq struct {
	ChatID string `json:"chat_id"`
	Text   string `json:"text"`
	Sender string `json:"sender"`
}

func writeJSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}

func (h *Handler) PostMessage(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req postMessageReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.ChatID == "" || req.Text == "" {
		http.Error(w, "invalid payload", http.StatusBadRequest)
		return
	}
	msg := store.Message{ID: time.Now().Format("20060102150405.000000"), ChatID: req.ChatID, Text: req.Text, Sender: req.Sender, CreatedAt: time.Now().UTC()}
	h.mem.AddMessage(msg)
	writeJSON(w, http.StatusOK, msg)
}

func (h *Handler) ListMessages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	chatID := r.URL.Query().Get("chat_id")
	if chatID == "" {
		http.Error(w, "chat_id required", http.StatusBadRequest)
		return
	}
	writeJSON(w, http.StatusOK, h.mem.ListMessages(chatID))
}
