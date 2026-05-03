package httpapi

import (
	"encoding/json"
	"net/http"

	"vant2/services/api/internal/auth"
	"vant2/services/api/internal/chat"
	"vant2/services/api/internal/store"
	"vant2/services/api/internal/ws"
)

func NewRouter() http.Handler {
	mem := store.NewMemory()
	authH := auth.NewHandler(mem)
	chatH := chat.NewHandler(mem)
	wsHub := ws.NewHub()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/v1/auth/send-otp", authH.SendOTP)
	mux.HandleFunc("/v1/auth/verify-otp", authH.VerifyOTP)
	mux.HandleFunc("/v1/chats", auth.RequireAuth(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode([]map[string]string{{"id": "1", "title": "Design Team"}, {"id": "2", "title": "Family"}})
	}))
	mux.HandleFunc("/v1/messages", auth.RequireAuth(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			chatH.PostMessage(w, r)
			return
		}
		chatH.ListMessages(w, r)
	}))
	mux.HandleFunc("/v1/ws", wsHub.ServeWS)
	return mux
}
