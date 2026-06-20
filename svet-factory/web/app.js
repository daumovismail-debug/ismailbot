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

async function init() {
  try {
    const st = await (await fetch("/api/status")).json();
    const badge = $("#mode");
    if (st.mode === "real") {
      const on = [];
      if (st.openclaw) on.push("OpenClaw (подписка)");
      if (st.openai) on.push("ChatGPT API");
      if (st.xai) on.push("Grok API");
      if (st.elevenlabs) on.push("ElevenLabs");
      badge.textContent = "● реальный режим: " + on.join(" + ");
      badge.className = "badge real";
    } else {
      badge.textContent = "● демо-режим (нет генераторов)";
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
}

async function start() {
  $("#start").disabled = true;
  $("#board").classList.remove("hidden");
  selected = null;
  const theme = $("#theme").value.trim();
  try {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) {
      const msg = res.status === 429
        ? "Сервер занят (слишком много задач). Попробуй чуть позже."
        : `Не удалось запустить (HTTP ${res.status}).`;
      $("#progressText").textContent = "⚠️ " + msg;
      $("#start").disabled = false;
      return;
    }
    const { id } = await res.json();
    poll(id);
  } catch (_) {
    $("#progressText").textContent = "⚠️ Сеть недоступна. Проверь соединение.";
    $("#start").disabled = false;
  }
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
      // после нескольких подряд неудач — прекращаем опрос, не зависаем молча
      if (++fails >= 5) {
        clearInterval(timer);
        $("#progressText").textContent = "⚠️ Потеряна связь с сервером.";
        $("#start").disabled = false;
      }
      return;
    }
    render();
    if (job.status === "done" || job.status === "error") {
      clearInterval(timer);
      $("#start").disabled = false;
    }
  };
  tick();
  timer = setInterval(tick, 1500);
}

function runningIndex() {
  const i = job.modules.findIndex((m) => m.status === "running");
  if (i >= 0) return i;
  // если ничего не бежит — последний завершённый/ошибочный
  let last = 0;
  job.modules.forEach((m, idx) => {
    if (m.status === "done" || m.status === "error") last = idx;
  });
  return last;
}

function render() {
  if (!job) return;
  // полоса модулей
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

  // прогресс
  $("#progressFill").style.width = (job.progress || 0) + "%";
  const cur = job.modules[runningIndex()];
  let txt = "";
  if (job.status === "done") txt = "✅ Готово! Открой модуль МОНТАЖ — там ролик.";
  else if (job.status === "error") txt = "⚠️ " + (job.error || "ошибка");
  else txt = `${cur.name}: ${cur.detail || "в работе…"}`;
  $("#progressText").textContent = txt;

  renderInspector(activeIdx);
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
           <div class="scene-voice">${esc(s.voice)}</div></div>`).join("");
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
    case "ГЕРОЙ":
      html += media.hero
        ? `<div class="grid"><div class="tile"><img src="${esc(media.hero)}"></div></div>`
        : tilePlaceholder(m, 1);
      break;
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
        html += `<video class="player" controls playsinline src="${esc(media.video)}"></video>
                 <a class="dl" href="${esc(media.video)}" download>⬇ Скачать ролик</a>`;
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

$("#start").addEventListener("click", start);
init();
