# Vant2

Vant2 — быстрый мобильный мессенджер с уникальным интерфейсом, анимациями уровня Telegram и архитектурой для масштабирования под App Store.

## Цели MVP

- Регистрация по номеру телефона (OTP)
- Личные чаты: текст, фото, видео, документы, голосовые
- Группы
- Статусы сообщений (sent/delivered/read)
- Push-уведомления APNs
- Поиск по сообщениям и чатам
- Блокировка пользователей и жалобы
- Уникальная дизайн-система и motion-язык

## Технический стек

- **iOS:** SwiftUI + UIKit bridge для performance-critical анимаций
- **Backend:** Go (REST + WebSocket)
- **DB:** PostgreSQL
- **Cache/Presence:** Redis
- **Media:** S3-compatible storage + CDN
- **Push:** APNs
- **Observability:** Sentry + Grafana

## Архитектура

- `apps/ios` — iOS-клиент
- `services/api` — HTTP API
- `services/realtime` — WebSocket gateway
- `services/media` — загрузка и выдача медиа
- `services/notify` — push-уведомления
- `infra` — Docker, конфиги окружений
- `docs` — PRD, API-контракты, motion-spec

## Motion & UI принципы

1. **60 FPS baseline**, 120Hz-ready на ProMotion
2. Spring-анимации для навигации и карточек
3. Hero transitions между списком чатов и экраном чата
4. Haptic feedback для key actions
5. Анимированные typing/reaction/read states

## План релизов

### Sprint 1
- Базовая архитектура проекта
- Авторизация + профиль
- Список чатов + экран диалога (текст)

### Sprint 2
- Медиа-вложения
- Группы
- Реакции и reply

### Sprint 3
- Поиск
- Push
- Модерация/блокировки

### Sprint 4
- Hardening, performance tuning
- App Store release readiness

## App Store readiness checklist

- Privacy Policy и Terms
- Age rating
- Data collection disclosure (App Privacy)
- Crash-free > 99%
- Стабильные push и background handling
- Контент-модерация (report/block)
