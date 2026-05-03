# Vant2 Web (Stage 1)

## Локально
1. API: `cd services/api && go run ./cmd/server`
2. Web: открой `apps/web/index.html`

## Render деплой (фикс ошибки go.mod)
Ошибка `go.mod file not found` возникает, когда Render билдит из корня репозитория.

Используй:
- `Root Directory`: `services/api` для API-сервиса
- `Build Command`: `go build -o app ./cmd/server`
- `Start Command`: `./app`

Либо подключи `render.yaml` из корня репо — он уже содержит верные настройки для API и web.

## Прод API URL
По умолчанию web-клиент использует `https://vant2.onrender.com`.
Переопределение:
```html
<script>window.VANT2_API_URL = 'https://your-api.onrender.com';</script>
<script src="app.js"></script>
```
