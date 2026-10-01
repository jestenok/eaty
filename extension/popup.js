"use strict";

const urlInput = document.getElementById("url");
const statusEl = document.getElementById("status");
const lastEl = document.getElementById("last");
const seenEl = document.getElementById("seen");
const SOURCES = { json: "данные Wolt", embedded: "данные в странице", page: "страница заказа" };

function show(el, text, cls) {
  el.textContent = text;
  el.className = cls || "muted";
}

const time = (iso) => new Date(iso).toLocaleTimeString("ru-RU");

async function load() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: "http://localhost:8080" });
  urlInput.value = appUrl;
  const { lastSync, seen = [] } = await chrome.storage.local.get(["lastSync", "seen"]);
  if (lastSync) {
    const when = new Date(lastSync.at).toLocaleString("ru-RU");
    const where = lastSync.url ? ` в ${lastSync.url}` : "";
    if (lastSync.ok) show(lastEl, `Последняя отправка ${when}${where}: заказов ${lastSync.result.orders}, в «Дома» ${lastSync.result.pantry_items}.`, "ok");
    else show(lastEl, `Последняя отправка ${when}${where} не удалась: ${lastSync.error}`, "err");
  }
  if (seen.length) {
    seenEl.replaceChildren(...seen.map((s) => {
      const li = document.createElement("li");
      li.textContent = `${time(s.at)} ${SOURCES[s.source] || s.source}: ${s.path} — ${s.orders ? `заказов: ${s.orders}` : "заказа нет"}`;
      return li;
    }));
  }
}

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.sync.set({ appUrl: urlInput.value.trim() || "http://localhost:8080" });
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

// Everything the popup shows plus the shape (keys and types, no values) of the last Wolt
// response where no order was recognized: enough to teach the extension a new format.
document.getElementById("debug").addEventListener("click", async () => {
  const { lastSync, seen, lastShape } = await chrome.storage.local.get(["lastSync", "seen", "lastShape"]);
  const { version } = chrome.runtime.getManifest();
  let shape = lastShape && lastShape.shape;
  try { shape = JSON.parse(shape); } catch (_) { /* cut at 20 KB, keep the text */ }
  const report = JSON.stringify({ version, lastSync, seen, lastShape: lastShape && { path: lastShape.path, shape } }, null, 2);
  try {
    await navigator.clipboard.writeText(report);
    show(document.getElementById("copied"), "Скопировано — вставь в чат.", "small ok");
  } catch (err) {
    show(document.getElementById("copied"), `Не скопировалось: ${err.message}`, "small err");
  }
});

load();
