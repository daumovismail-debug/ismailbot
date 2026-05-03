package ws

import (
	"encoding/json"
	"net/http"
	"sync/atomic"
)

type Hub struct {
	connections int64
}

func NewHub() *Hub { return &Hub{} }

// ServeWS currently returns a realtime handshake payload.
// Next iteration: upgrade to real websocket transport.
func (h *Hub) ServeWS(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	atomic.AddInt64(&h.connections, 1)
	defer atomic.AddInt64(&h.connections, -1)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"status": "ready",
		"transport": "polling-fallback",
		"note": "websocket upgrade pending",
	})
}

func (h *Hub) ActiveConnections() int64 {
	return atomic.LoadInt64(&h.connections)
}
