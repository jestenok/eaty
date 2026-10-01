"use strict";

const urlInput = document.getElementById("url");
const statusEl = document.getElementById("status");
const lastEl = document.getElementById("last");

function show(el, text, cls) {
  el.textContent = text;
  el.className = cls || "muted";
}

async function load() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: "http://localhost:8080" });
  urlInput.value = appUrl;
  const { lastSync } = await chrome.storage.local.get("lastSync");
  if (lastSync) {
    const when = new Date(lastSync.at).toLocaleString("ru-RU");
    if (lastSync.ok) show(lastEl, `Последняя отправка ${when}: заказов ${lastSync.result.orders}, в «Дома» ${lastSync.result.pantry_items}.`, "ok");
    else show(lastEl, `Последняя отправка ${when} не удалась: ${lastSync.error}`, "err");
  }
}

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.sync.set({ appUrl: urlInput.value.trim() || "http://localhost:8080", appUrlManual: Boolean(urlInput.value.trim()) });
  show(statusEl, "Сохранено.", "ok");
});

document.getElementById("check").addEventListener("click", async () => {
  const base = (urlInput.value.trim() || "http://localhost:8080").replace(/\/+$/, "");
  try {
    const resp = await fetch(`${base}/api/v1/health`);
    show(statusEl, resp.ok ? "Приложение на связи ♡" : `Ответ ${resp.status}`, resp.ok ? "ok" : "err");
  } catch (err) {
    show(statusEl, `Не достучаться: ${err.message}. Приложение запущено?`, "err");
  }
});

load();
