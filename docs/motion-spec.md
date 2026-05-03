# Vant2 Motion Spec v0.1

## Навигация

- Переход в чат: spring (response 0.38, damping 0.82)
- Назад: интерактивный edge-swipe
- Tab switch: crossfade + 8pt slide

## Сообщения

- Incoming bubble: opacity 0->1 + y 8->0 за 180ms
- Outgoing bubble: scale 0.98->1 + opacity 0->1 за 160ms
- Read status icon morph: 120ms

## Инпут/клавиатура

- Composer follows keyboard curve exactly
- Attach panel reveal: spring 240ms

## Реакции

- Long press -> menu reveal 140ms
- Reaction burst: scale 0.7->1.05->1 за 220ms

## Производительность

- Не более 4 одновременно активных implicit animation layers на экране чата
- Предзагрузка аватаров и медиа-превью перед push transition
