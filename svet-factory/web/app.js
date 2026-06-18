const $ = (s) => document.querySelector(s);

async function init() {
  // режим (реальный / демо)
  try {
    const st = await (await fetch("/api/status")).json();
    const badge = $("#mode");
    if (st.mode === "real") {
      const on = [];
      if (st.openai) on.push("ChatGPT");
      if (st.xai) on.push("Grok");
      if (st.elevenlabs) on.push("ElevenLabs");
      badge.textContent = "● реальный режим: " + on.join(" + ");
      badge.className = "badge real";
    } else {
      badge.textContent = "● демо-режим (вставь API-ключи в .env)";
      badge.className = "badge demo";
    }
  } catch (_) {}

  // банк идей в подсказки
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

let timer = null;

async function start() {
  const theme = $("#theme").value.trim();
  $("#start").disabled = true;
  $("#board").classList.remove("hidden");
  $("#result").classList.add("hidden");

  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  });
  const { id } = await res.json();
  poll(id);
}

async function poll(id) {
  clearInterval(timer);
  timer = setInterval(async () => {
    const job = await (await fetch(`/api/jobs/${id}`)).json();
    render(job);
    if (job.status === "done" || job.status === "error") {
      clearInterval(timer);
      $("#start").disabled = false;
      if (job.status === "done") showVideo(id);
    }
  }, 1200);
}

function render(job) {
  const ol = $("#modules");
  ol.innerHTML = "";
  job.modules.forEach((m) => {
    const li = document.createElement("li");
    li.className = `mod ${m.status}`;
    li.innerHTML = `<span class="dot"></span>
      <span class="name">${m.name}</span>
      <span class="detail">${m.detail || statusLabel(m.status)}</span>`;
    ol.appendChild(li);
  });
}

function statusLabel(s) {
  return { pending: "ожидает", running: "в работе…", done: "готово", error: "ошибка" }[s] || "";
}

function showVideo(id) {
  $("#result").classList.remove("hidden");
  const url = `/api/jobs/${id}/video`;
  $("#player").src = url;
  $("#download").href = url;
}

$("#start").addEventListener("click", start);
init();
