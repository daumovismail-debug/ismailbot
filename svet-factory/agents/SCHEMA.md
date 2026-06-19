# 📐 КАНОНИЧЕСКИЙ КОНТРАКT (единая истина по полям) — ВСЕ агенты следуют этому

> Решает нестыковки между агентами: одни имена полей, одни пороги, один формат.
> Если в рецепте агента поле названо иначе — **приоритет у этого файла**.

## Ключ кадра
- Кадр идентифицируется полем **`id`** (целое, 1..N). НЕ `shot`. Везде — `id`.
- У кадра может быть **несколько реплик** → массив `lines[]` с `line_id`.

## Единый объект серии (через него идёт всё)
```json
{
  "episode_id":"ep_001","project":"...","episode_n":1,
  "prev_cliffhanger":"...",                         // связь с прошлой серией
  "brief":{...}, "season_arc":{...}, "cast":{...},
  "music_mood":"...", "platform_targets":["tiktok","reels","shorts"],
  "shots":[
    {
      "id":1,"act":"COLD OPEN","t":"0-3",
      "characters":["heroine"],                     // Сценарист
      "action":"что в кадре","light":"anger",       // light = ENUM (см. ниже)
      "lines":[{"line_id":"1a","character":"heroine","voice_kz":"...","voice_ru":"...","emotion":"anger"}],
      "image_prompt":"...","references":["heroine"], // Художник
      "camera":"push-in","motion":"...","light_anim":"...","transition":"hard cut",
      "continuity":"...","beat_hit":true,            // Аниматор
      "audio_dur":2.6,"voice_id":"VOICE_HEROINE","word_timings":[],"split_into":[], // Голос
      "duration":3,                                  // = max(audio_dur+pause, 3), cap 15
      "image_path":null,"video_path":null,"audio_path":null,
      "qc":{"status":"pending","face_match":null,"issues":[],"retries":0} // Контролёр
    }
  ],
  "edl":{"timeline":[{"id":1,"in":0,"out":3,"subtitle":"...","sub_style":"karaoke","overlay":null}]},
  "publish":{"post_url":null,"post_id":null,...}
}
```
**Правило записи:** каждый агент **патчит свои поля в `shots[]` по `id`** (не создаёт
свой отдельный список). Голос пишет в кадр, не в параллельный массив.

## ENUM «свет = эмоция» (единый, источник — project-bible)
`happy · sad · anger · shock · fear · hope · despair · resolve · contempt`
Сценарист в поле `light` ставит ТОЛЬКО значение из этого списка. Художник и
Аниматор берут визуал/анимацию света по этому enum из project-bible.

## Длительность и длина
- **Длина серии: 45–60 сек** (единый стандарт; НЕ 45–90).
- **Клип кадра:** `duration = max(audio_dur + pause_after, 3)`, **максимум 15 сек**.
  Не влезает реплика → `split_into:["7a","7b"]` (Голос задаёт, Аниматор делит).

## Lip-sync
- Голос отдаёт **`word_timings`** (тайминги слов) или SRT — иначе синхрон губ и
  порог av_sync ≤120мс недостижимы из одного числа.
- `lipsync` — свойство ВИДЕО, владелец **Аниматор** (не Голос).

## Пороги качества (Контролёр) — одна шкала
- **`face_match` = косинус 0..1** (ArcFace для людей / CLIP для не-людей).
- **Порог PASS ≥ 0.60.** (строго 0.95 / мягко 0.40). Шкалы «0–100/≥85» НЕ используем.
- Артефакты/чёткость/av_sync — как в controller.md. Вердикт пишется в `shots[].qc`.

## Источники истины (кто канон)
- Облик/каста/voice_id/enum света → **project-bible.md** (+ ведёт Кастинг).
- Связка/состояние/чекпоинты → **orchestration.md**.
- Движки → **engines.md**. Данные/метрики → **data-schema.md**.
- При конфликте: **SCHEMA.md > orchestration.md > рецепт агента**.

## Обязательные связи (которых не хватало)
- Сценарист добавляет: `episode_n`, `prev_cliffhanger`, `characters[]`, `light`(enum).
- Художник: `references[]` обязателен; Аниматор тоже несёт `references[]` (лок лица).
- Контролёр **блокирует рендер**, если у персонажа нет эталона (reference) в касте.
- Издатель пишет `post_url`+`post_id` → они уходят в data-schema → Аналитик.
- Качество (`qc`) логируется в data-schema (face_match_avg, retries, fail_reasons).
