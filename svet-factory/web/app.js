const $ = (s) => document.querySelector(s);

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
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  });
  const { id } = await res.json();
  poll(id);
}

function poll(id) {
  clearInterval(timer);
  const tick = async () => {
    try {
      job = await (await fetch(`/api/jobs/${id}`)).json();
    } catch (_) {
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
      <span><span class="num">${idx + 1}</span> <span class="label">${m.name}</span></span>`;
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
  let html = `<h3>${idx + 1}. ${m.name}</h3>`;

  switch (m.name) {
    case "ИДЕЯ":
      html += ctx.idea
        ? `<div class="note"><b>${ctx.idea.theme}</b><br>${ctx.idea.message}</div>`
        : note(m);
      if (ctx.brief) html += `<div class="scene-row"><div class="scene-role">Бриф режиссёра</div>
        <div class="scene-prompt">тон: ${ctx.brief.tone || ""} · конфликт: ${ctx.brief.core_conflict || ""} · эмоция: ${ctx.brief.target_emotion || ""}</div></div>`;
      break;
    case "СЦЕНАРИЙ":
      if (ctx.scenes) {
        html += ctx.scenes.map((s) =>
          `<div class="scene-row"><div class="scene-role">${s.role}</div>
           <div class="scene-voice">${s.voice}</div></div>`).join("");
      } else html += note(m);
      break;
    case "РАСКАДРОВКА":
      if (ctx.storyboard) {
        html += ctx.storyboard.map((s) =>
          `<div class="scene-row"><div class="scene-role">${s.role}</div>
           <div class="scene-prompt">🎨 ${s.image_prompt}</div>
           <div class="scene-prompt">🎬 ${s.motion_prompt}</div></div>`).join("");
      } else html += note(m);
      break;
    case "ГЕРОЙ":
      html += media.hero
        ? `<div class="grid"><div class="tile"><img src="${media.hero}"></div></div>`
        : tilePlaceholder(m, 1);
      break;
    case "КАРТИНКИ": {
      const total = (ctx.scenes && ctx.scenes.length) || 5;
      const imgs = media.scenes || [];
      html += `<div class="grid">`;
      for (let i = 0; i < total; i++) {
        if (imgs[i]) html += `<div class="tile"><img src="${imgs[i]}"></div>`;
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
          `<div class="tile"><video src="${c}" muted loop autoplay playsinline></video></div>`).join("") + `</div>`;
      } else {
        html += `<div class="note">${m.detail || "Плавный зум (Ken Burns) по кадрам — применится на монтаже."}</div>`;
      }
      break;
    case "ЗВУК":
      html += `<div class="note">${m.detail || "Озвучка реплик."}</div>`;
      break;
    case "КОНТРОЛЬ": {
      const qc = ctx.qc;
      html += `<div class="note">${m.detail || note(m)}</div>`;
      if (qc) html += `<div class="note">Кадры: ${qc.frames_ok}/${qc.frames_total}${qc.demo ? " (демо-плейсхолдеры)" : ""}${(qc.issues||[]).length ? " · ⚠️ " + qc.issues.join(", ") : " · ✅"}</div>`;
      break;
    }
    case "АНАЛИТИК": {
      const f = ctx.forecast;
      if (f) {
        html += `<div class="scene-row"><div class="scene-role">Прогноз хука</div>
          <div class="scene-voice">${f.hook_score}/100 — ${f.verdict || ""}</div></div>`;
        if (f.predicted_intro_retention) html += `<div class="scene-prompt">удержание 3с: ${f.predicted_intro_retention}</div>`;
        if (f.fixes) html += `<div class="note">Советы: ${(f.fixes||[]).join("; ")}</div>`;
      } else html += note(m);
      break;
    }
    case "ПУБЛИКАЦИЯ": {
      const p = ctx.publish;
      if (p) {
        html += `<div class="scene-row"><div class="scene-role">Подпись</div><div class="scene-voice">${p.caption || ""}</div></div>`;
        if (p.hashtags) html += `<div class="scene-row"><div class="scene-prompt">${(p.hashtags||[]).join(" ")}</div></div>`;
        if (p.first_comment) html += `<div class="scene-row"><div class="scene-role">1-й коммент</div><div class="scene-voice">${p.first_comment}</div></div>`;
        if (p.post_time) html += `<div class="scene-row"><div class="scene-prompt">🕒 ${p.post_time}</div></div>`;
        html += `<div class="note">Постинг — вручную/планировщиком (API соцсетей ограничены).</div>`;
      } else html += note(m);
      break;
    }
    case "МОНТАЖ":
      if (media.video) {
        html += `<video class="player" controls playsinline src="${media.video}"></video>
                 <a class="dl" href="${media.video}" download>⬇ Скачать ролик</a>`;
      } else html += note(m);
      break;
    default:
      html += note(m);
  }
  box.innerHTML = html;
}

function note(m) {
  const label = { pending: "ожидает очереди", running: "в работе…", done: "готово", error: "ошибка" }[m.status] || "";
  return `<div class="note">${m.detail || label}</div>`;
}
function tilePlaceholder(m, n) {
  let t = "";
  for (let i = 0; i < n; i++)
    t += `<div class="tile ${m.status === "running" ? "loading" : "empty"}"></div>`;
  return `<div class="grid">${t}</div>`;
}

$("#start").addEventListener("click", start);
init();
