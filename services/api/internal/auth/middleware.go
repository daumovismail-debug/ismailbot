package auth

import (
	"context"
	"net/http"
	"strings"
)

type contextKey string

const UserPhoneKey contextKey = "user_phone"

func RequireAuth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		if !strings.HasPrefix(authHeader, "Bearer ") {
			http.Error(w, "missing bearer token", http.StatusUnauthorized)
			return
		}
		token := strings.TrimPrefix(authHeader, "Bearer ")
		phone, ok := ParseDevToken(token)
		if !ok {
			http.Error(w, "invalid token", http.StatusUnauthorized)
			return
		}
		ctx := context.WithValue(r.Context(), UserPhoneKey, phone)
		next(w, r.WithContext(ctx))
	}
}
