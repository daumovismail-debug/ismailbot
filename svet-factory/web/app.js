const $ = (s) => document.querySelector(s);

// экранируем любой текст от модели/пользователя перед вставкой в innerHTML
function esc(v) {
  if (v == null) return "";
  return String(v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

let timer = null;
let job = null;          // последний статус задачи
let selected = null;     // вручную выбранный модуль (индекс) или null = авто
let resultShown = false; // результат уже свернул таймлайн?

// ---------- маршрутизация между экранами ----------
function showHome() {
  clearInterval(timer);
  $("#board").classList.add("hidden");
  $("#home").classList.remove("hidden");
  loadLibrary();
}
function showBoard() {
  $("#home").classList.add("hidden");
  $("#board").classList.remove("hidden");
}

// ---------- инициализация ----------
async function init() {
  try {
    const st = await (await fetch("/api/status")).json();
    const badge = $("#mode");
    if (st.mode === "real") {
      const on = [];
      if (st.openclaw) on.push("OpenClaw");
      if (st.openai) on.push("ChatGPT API");
      if (st.xai) on.push("Grok");
      if (st.elevenlabs) on.push("ElevenLabs");
      badge.textContent = "● реальный режим · " + on.join(" + ");
      badge.className = "badge real";
    } else {
      badge.textContent = "● демо-режим";
      badge.className = "badge demo";
    }
  } catch (_) {}

  try {
    const ideas = await (await fetch("/api/ideas")).json();
    const dl = $("#ideas");
    ideas.forEach((i) => {
      const o = document.createElement("option");
      o.value = i.theme;
      dl.appendChild(o);
    });
  } catch (_) {}

  $("#start").addEventListener("click", start);
  $("#back").addEventListener("click", showHome);
  $("#brandHome").addEventListener("click", showHome);
  loadLibrary();
}

// ---------- библиотека сериалов ----------
async function loadLibrary() {
  let jobs = [];
  try {
    const r = await fetch("/api/jobs");
    if (r.ok) jobs = await r.json();
  } catch (_) {}
  const grid = $("#libGrid");
  grid.innerHTML = "";
  $("#libCount").textContent = jobs.length ? `${jobs.length}` : "";
  $("#libEmpty").classList.toggle("hidden", jobs.length > 0);
  const label = { done: "готово", running: "в работе", error: "ошибка", queued: "в очереди" };
  jobs.forEach((j, i) => {
    const m = j.media || {};
    const thumb = m.hero ? `<img src="${esc(m.hero)}">` : `<div class="ph">✦</div>`;
    const el = document.createElement("div");
    el.className = "card";
    el.style.animationDelay = (i * 0.04) + "s";
    el.innerHTML = `<div class="card-thumb">${thumb}</div>
      <div class="card-body">
        <div class="card-theme">${esc(j.theme || "Без темы")}</div>
        <span class="chip ${esc(j.status)}">${label[j.status] || esc(j.status)}</span>
      </div>`;
    el.onclick = () => openJob(j.id);
    grid.appendChild(el);
  });
}

// ---------- создание / открытие серии ----------
async function start() {
  const theme = $("#theme").value.trim();
  $("#start").disabled = true;
  $("#createNote").textContent = "";
  try {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) {
      $("#createNote").textContent = res.status === 429
        ? "⚠️ Сервер занят — попробуй чуть позже."
        : `⚠️ Не удалось запустить (HTTP ${res.status}).`;
      $("#start").disabled = false;
      return;
    }
    const { id } = await res.json();
    $("#theme").value = "";
    $("#start").disabled = false;
    openJob(id);
  } catch (_) {
    $("#createNote").textContent = "⚠️ Сеть недоступна.";
    $("#start").disabled = false;
  }
}

function openJob(id) {
  selected = null;
  job = null;
  resultShown = false;
  $("#result").classList.add("hidden");
  $("#stagesWrap").open = true;
  $("#boardTitle").textContent = "Загрузка…";
  $("#inspector").innerHTML = "";
  $("#stepper").innerHTML = "";
  $("#progressFill").style.width = "0%";
  $("#progressText").textContent = "";
  showBoard();
  poll(id);
}

function poll(id) {
  clearInterval(timer);
  let fails = 0;
  const tick = async () => {
    try {
      const res = await fetch(`/api/jobs/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      job = await res.json();
      fails = 0;
    } catch (_) {
      if (++fails >= 5) {
        clearInterval(timer);
        $("#progressText").textContent = "⚠️ Потеряна связь с сервером.";
      }
      return;
    }
    render();
    // awaiting_cast — пауза для пользователя: прекращаем опрос, форма стабильна
    if (["done", "error", "awaiting_cast"].includes(job.status)) clearInterval(timer);
  };
  tick();
  timer = setInterval(tick, 1500);
}

function runningIndex() {
  const i = job.modules.findIndex((m) => m.status === "running");
  if (i >= 0) return i;
  let last = 0;
  job.modules.forEach((m, idx) => {
    if (m.status === "done" || m.status === "error") last = idx;
  });
  return last;
}

function render() {
  if (!job) return;
  $("#boardTitle").textContent = job.theme || "Серия";

  const stepper = $("#stepper");
  stepper.innerHTML = "";
  const activeIdx = selected != null ? selected : runningIndex();
  job.modules.forEach((m, idx) => {
    const el = document.createElement("div");
    el.className = `step ${m.status}${idx === activeIdx ? " active" : ""}`;
    el.innerHTML = `<span class="dot"></span>
      <span><span class="num">${idx + 1}</span> <span class="label">${esc(m.name)}</span></span>`;
    el.onclick = () => { selected = idx; render(); };
    stepper.appendChild(el);
  });

  $("#progressFill").style.width = (job.progress || 0) + "%";
  const cur = job.modules[runningIndex()];
  let txt = "";
  if (job.status === "done") txt = "✅ Готово — ролик ниже.";
  else if (job.status === "error") txt = "⚠️ " + (job.error || "ошибка");
  else if (job.status === "awaiting_cast") txt = "⏸ Жду подтверждения касты ↓";
  else txt = `${cur.name}: ${cur.detail || "в работе…"}`;
  $("#progressText").textContent = txt;

  renderInspector(activeIdx);
  if (job.status === "awaiting_cast") renderCasting();
  else renderResult();
}

// ---------- кастинг: подтверждение персонажей ----------
function renderCasting() {
  const box = $("#result");
  const cast = (job.context && job.context.cast) || [];
  const rows = cast.map((c, i) => `
    <div class="cast-card">
      <div class="cast-head">${esc(c.name)}
        <span class="cast-type">${esc(c.type)}${c.auto ? " · авто" : ""}</span></div>
      <input class="cast-in" data-i="${i}" data-k="name" value="${esc(c.name)}" placeholder="Имя / роль">
      <input class="cast-in" data-i="${i}" data-k="face" value="${esc(c.face)}" placeholder="Внешность (лицо, волосы)">
      <input class="cast-in" data-i="${i}" data-k="outfit" value="${esc(c.outfit)}" placeholder="Наряд / фишка">
      <input class="cast-in" data-i="${i}" data-k="character" value="${esc(c.character || "")}" placeholder="Характер">
    </div>`).join("");
  box.innerHTML = `
    <div class="cast-title">🎭 Кастинг — подтверди персонажей</div>
    <div class="cast-hint">Героиня — твой бренд-герой (не меняется). Поправь второстепенных
      или нажми «Пусть решит сам».</div>
    <div class="cast-grid">${rows}</div>
    <div class="result-actions">
      <button class="act primary" id="castSave">✓ Сохранить и продолжить</button>
      <button class="act" id="castAuto">⚡ Пусть решит сам</button>
    </div>`;
  box.classList.remove("hidden");

  $("#castSave").onclick = () => {
    const draft = JSON.parse(JSON.stringify(cast));
    box.querySelectorAll(".cast-in").forEach((inp) => {
      draft[+inp.dataset.i][inp.dataset.k] = inp.value;
    });
    submitCast(draft);
  };
  $("#castAuto").onclick = () => submitCast(null);
}

async function submitCast(cast) {
  const sb = $("#castSave"), au = $("#castAuto");
  if (sb) sb.disabled = true;
  if (au) au.disabled = true;
  try {
    await fetch(`/api/jobs/${job.id}/cast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cast }),
    });
  } catch (_) {}
  $("#result").classList.add("hidden");
  $("#stagesWrap").open = true;
  poll(job.id);   // возобновляем опрос — конвейер продолжился
}

// ---------- экран результата ----------
function renderResult() {
  const box = $("#result");
  const media = job.media || {};
  const ctx = job.context || {};
  if (!(job.status === "done" && media.video)) {
    box.classList.add("hidden");
    return;
  }
  const p = ctx.publish || {};
  const r = ctx.review || {};
  let html = `<video controls playsinline src="${esc(media.video)}"></video>
    <div class="result-actions">
      <a class="act primary" href="${esc(media.video)}" download>⬇ Скачать</a>`;
  if (p.telegram_url)
    html += `<a class="act tg" href="${esc(p.telegram_url)}" target="_blank" rel="noopener">✈ В Telegram</a>`;
  if (p.caption)
    html += `<button class="act" id="copyCap">⧉ Копировать подпись</button>`;
  html += `</div>`;
  if (r.vibe_score != null) {
    const ok = r.accepted;
    html += `<div class="verdict">Приёмка Режиссёра:
      <b class="${ok ? "ok" : "no"}">${ok ? "✅ принято" : "⚠️ на доработку"}</b>
      · вайб ${esc(r.vibe_score)}/100</div>`;
  }
  if (p.caption)
    html += `<div class="result-caption">${esc(p.caption)}<br>${esc((p.hashtags || []).join(" "))}</div>`;
  box.innerHTML = html;
  box.classList.remove("hidden");

  const cb = $("#copyCap");
  if (cb) cb.onclick = () => {
    const text = (p.caption || "") + "\n" + (p.hashtags || []).join(" ");
    if (navigator.clipboard) navigator.clipboard.writeText(text);
    cb.textContent = "✓ Скопировано";
    setTimeout(() => { cb.textContent = "⧉ Копировать подпись"; }, 1500);
  };
  if (!resultShown) { $("#stagesWrap").open = false; resultShown = true; }
}

function renderInspector(idx) {
  const m = job.modules[idx];
  const ctx = job.context || {};
  const media = job.media || {};
  const box = $("#inspector");
  let html = `<h3>${idx + 1}. ${esc(m.name)}</h3>`;

  switch (m.name) {
    case "ИДЕЯ":
      html += ctx.idea
        ? `<div class="note"><b>${esc(ctx.idea.theme)}</b><br>${esc(ctx.idea.message)}</div>`
        : note(m);
      if (ctx.brief) html += `<div class="scene-row"><div class="scene-role">Бриф режиссёра</div>
        <div class="scene-prompt">тон: ${esc(ctx.brief.tone)} · конфликт: ${esc(ctx.brief.core_conflict)} · эмоция: ${esc(ctx.brief.target_emotion)}</div></div>`;
      break;
    case "СЦЕНАРИЙ":
      if (ctx.scenes) {
        html += ctx.scenes.map((s) =>
          `<div class="scene-row"><div class="scene-role">${esc(s.role)}</div>
           <div class="scene-voice">🇰🇿 ${esc(s.voice)}</div>
           ${s.voice_ru && s.voice_ru !== s.voice
             ? `<div class="scene-prompt">🇷🇺 ${esc(s.voice_ru)}</div>` : ""}</div>`).join("");
      } else html += note(m);
      break;
    case "РАСКАДРОВКА":
      if (ctx.storyboard) {
        html += ctx.storyboard.map((s) =>
          `<div class="scene-row"><div class="scene-role">${esc(s.role)}</div>
           <div class="scene-prompt">🎨 ${esc(s.image_prompt)}</div>
           <div class="scene-prompt">🎬 ${esc(s.motion_prompt)}</div></div>`).join("");
      } else html += note(m);
      break;
    case "ГЕРОЙ": {
      const tiles = [];
      if (media.hero) tiles.push(`<div class="tile"><img src="${esc(media.hero)}"></div>`);
      if (media.model_sheet) tiles.push(`<div class="tile"><img src="${esc(media.model_sheet)}"></div>`);
      (media.chars || []).forEach((c) => tiles.push(`<div class="tile"><img src="${esc(c)}"></div>`));
      html += tiles.length ? `<div class="grid">${tiles.join("")}</div>` : tilePlaceholder(m, 2);
      (ctx.cast || []).forEach((h) => {
        html += `<div class="scene-row"><div class="scene-role">${esc(h.name)} · ${esc(h.type)}</div>
          <div class="scene-prompt">${esc(h.face)}</div>
          <div class="scene-prompt">наряд: ${esc(h.outfit)} · голос: ${esc(h.voice_hint)}</div></div>`;
      });
      break;
    }
    case "КАРТИНКИ": {
      const total = (ctx.scenes && ctx.scenes.length) || 5;
      const imgs = media.scenes || [];
      html += `<div class="grid">`;
      for (let i = 0; i < total; i++) {
        if (imgs[i]) html += `<div class="tile"><img src="${esc(imgs[i])}"></div>`;
        else if (m.status === "running" && i === imgs.length)
          html += `<div class="tile loading"></div>`;
        else html += `<div class="tile empty"></div>`;
      }
      html += `</div>`;
      break;
    }
    case "АНИМАЦИЯ":
      if ((media.clips || []).length) {
        html += `<div class="grid">` + media.clips.map((c) =>
          `<div class="tile"><video src="${esc(c)}" muted loop autoplay playsinline></video></div>`).join("") + `</div>`;
      } else {
        html += `<div class="note">${esc(m.detail) || "Плавный зум (Ken Burns) по кадрам — применится на монтаже."}</div>`;
      }
      break;
    case "ЗВУК":
      html += `<div class="note">${esc(m.detail) || "Озвучка реплик."}</div>`;
      break;
    case "КОНТРОЛЬ": {
      const qc = ctx.qc;
      html += `<div class="note">${esc(m.detail) || esc(noteText(m))}</div>`;
      if (qc) html += `<div class="note">Кадры: ${esc(qc.frames_ok)}/${esc(qc.frames_total)}${qc.demo ? " (демо-плейсхолдеры)" : ""}${(qc.issues||[]).length ? " · ⚠️ " + esc(qc.issues.join(", ")) : " · ✅"}</div>`;
      break;
    }
    case "ПРИЁМКА": {
      const r = ctx.review;
      if (r) {
        const mark = r.accepted ? "✅ принято" : "⚠️ на доработку";
        html += `<div class="scene-row"><div class="scene-role">Вайб-приёмка Режиссёра</div>
          <div class="scene-voice">${mark} — ${esc(r.vibe_score)}/100</div></div>`;
        if ((r.notes || []).length)
          html += `<div class="note">Замечания: ${esc((r.notes || []).join("; "))}</div>`;
      } else html += note(m);
      break;
    }
    case "АНАЛИТИК": {
      const f = ctx.forecast;
      if (f) {
        html += `<div class="scene-row"><div class="scene-role">Прогноз хука</div>
          <div class="scene-voice">${esc(f.hook_score)}/100 — ${esc(f.verdict)}</div></div>`;
        if (f.predicted_intro_retention) html += `<div class="scene-prompt">удержание 3с: ${esc(f.predicted_intro_retention)}</div>`;
        if (f.fixes) html += `<div class="note">Советы: ${esc((f.fixes||[]).join("; "))}</div>`;
      } else html += note(m);
      break;
    }
    case "ПУБЛИКАЦИЯ": {
      const p = ctx.publish;
      if (p) {
        html += `<div class="scene-row"><div class="scene-role">Подпись</div><div class="scene-voice">${esc(p.caption)}</div></div>`;
        if (p.hashtags) html += `<div class="scene-row"><div class="scene-prompt">${esc((p.hashtags||[]).join(" "))}</div></div>`;
        if (p.first_comment) html += `<div class="scene-row"><div class="scene-role">1-й коммент</div><div class="scene-voice">${esc(p.first_comment)}</div></div>`;
        if (p.post_time) html += `<div class="scene-row"><div class="scene-prompt">🕒 ${esc(p.post_time)}</div></div>`;
        html += `<div class="note">Постинг — вручную/планировщиком (API соцсетей ограничены).</div>`;
      } else html += note(m);
      break;
    }
    case "МОНТАЖ":
      if (media.video) {
        html += `<video class="tile-video" controls playsinline src="${esc(media.video)}" style="width:100%;border-radius:14px;background:#000"></video>
                 <a class="act primary" style="display:inline-block;margin-top:12px" href="${esc(media.video)}" download>⬇ Скачать ролик</a>`;
      } else html += note(m);
      break;
    default:
      html += note(m);
  }
  box.innerHTML = html;
}

function noteText(m) {
  const label = { pending: "ожидает очереди", running: "в работе…", done: "готово", error: "ошибка" }[m.status] || "";
  return m.detail || label;
}
function note(m) {
  return `<div class="note">${esc(noteText(m))}</div>`;
}
function tilePlaceholder(m, n) {
  let t = "";
  for (let i = 0; i < n; i++)
    t += `<div class="tile ${m.status === "running" ? "loading" : "empty"}"></div>`;
  return `<div class="grid">${t}</div>`;
}

init();
