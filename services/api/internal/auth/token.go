package auth

import (
	"encoding/base64"
	"fmt"
	"strings"
)

func BuildDevToken(phone string) string {
	return base64.StdEncoding.EncodeToString([]byte(fmt.Sprintf("vant2:%s", phone)))
}

func ParseDevToken(token string) (string, bool) {
	b, err := base64.StdEncoding.DecodeString(token)
	if err != nil {
		return "", false
	}
	raw := string(b)
	if !strings.HasPrefix(raw, "vant2:") {
		return "", false
	}
	phone := strings.TrimPrefix(raw, "vant2:")
	return phone, phone != ""
}
