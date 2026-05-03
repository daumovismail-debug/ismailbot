package store

import (
	"testing"
	"time"
)

func TestOTPVerify(t *testing.T) {
	m := NewMemory()
	m.SaveOTP("+1000", "123456", time.Minute)
	if !m.VerifyOTP("+1000", "123456") {
		t.Fatal("expected otp to verify")
	}
	if m.VerifyOTP("+1000", "123456") {
		t.Fatal("otp must be single-use")
	}
}

func TestMessagesRoundtrip(t *testing.T) {
	m := NewMemory()
	m.AddMessage(Message{ID: "1", ChatID: "chat1", Text: "hello"})
	msgs := m.ListMessages("chat1")
	if len(msgs) != 1 || msgs[0].Text != "hello" {
		t.Fatalf("unexpected messages: %+v", msgs)
	}
}
