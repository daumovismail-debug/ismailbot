package store

import (
	"sync"
	"time"
)

type OTPRecord struct {
	Phone     string
	Code      string
	ExpiresAt time.Time
}

type Message struct {
	ID        string    `json:"id"`
	ChatID    string    `json:"chat_id"`
	Text      string    `json:"text"`
	Sender    string    `json:"sender"`
	CreatedAt time.Time `json:"created_at"`
}

type Memory struct {
	mu       sync.RWMutex
	otps     map[string]OTPRecord
	messages map[string][]Message
}

func NewMemory() *Memory {
	return &Memory{
		otps:     make(map[string]OTPRecord),
		messages: make(map[string][]Message),
	}
}

func (m *Memory) SaveOTP(phone, code string, ttl time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.otps[phone] = OTPRecord{Phone: phone, Code: code, ExpiresAt: time.Now().Add(ttl)}
}

func (m *Memory) VerifyOTP(phone, code string) bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	rec, ok := m.otps[phone]
	if !ok || time.Now().After(rec.ExpiresAt) || rec.Code != code {
		return false
	}
	delete(m.otps, phone)
	return true
}

func (m *Memory) AddMessage(msg Message) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.messages[msg.ChatID] = append(m.messages[msg.ChatID], msg)
}

func (m *Memory) ListMessages(chatID string) []Message {
	m.mu.RLock()
	defer m.mu.RUnlock()
	msgs := m.messages[chatID]
	out := make([]Message, len(msgs))
	copy(out, msgs)
	return out
}
