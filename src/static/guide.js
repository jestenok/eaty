"use strict";

// The guide checks what is already done: whether you're signed in here, whether the extension
// is on this page and whom it's signed in as. It talks to the extension the way the app does
// (see askExtension in app.js): its app-bridge.js answers each request "x" with "x-result".

const extensionVersion = () => document.documentElement.dataset.eatyExtension;

function askExtension(type, timeoutMs) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => finish(null), timeoutMs);
    function finish(result) {
      clearTimeout(timer);
      window.removeEventListener("message", onMessage);
      resolve(result);
    }
    function onMessage(event) {
      if (event.source === window && event.data && event.data.source === "eaty-extension"
          && event.data.type === `${type}-result`) finish(event.data.result || {});
    }
    window.addEventListener("message", onMessage);
    window.postMessage({ source: "eaty-app", type }, location.origin);
  });
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

async function signedIn() {
  try {
    const resp = await fetch("/api/v1/auth/me");
    return resp.ok ? await resp.json() : null;
  } catch (_) {
    return null;
  }
}

let me = null;
const box = document.getElementById("ext-status");
const connectBtn = document.getElementById("ext-connect");

function show(state, html, button) {
  box.className = `card status ${state}`;
  box.querySelector(".grow").innerHTML = html;
  connectBtn.hidden = !button;
  if (button) connectBtn.textContent = button;
}

async function checkExtension() {
  const version = extensionVersion();
  if (!version) {
    return show("missing", "Расширения на этой странице пока нет — начни с шага 1. Если оно уже стоит — обнови эту страницу.");
  }
  const status = await askExtension("extension-status", 5000);
  if (!status) {
    return show("missing", `Стоит старое расширение (${esc(version)}). Обнови его — как, написано ниже, в «Как обновить расширение».`);
  }
  if (!me) {
    return show("missing", `Расширение стоит (${esc(version)}). Теперь <a href="/">войди в eaty</a> и вернись сюда, чтобы подключить его.`);
  }
  if (status.login === me.login) {
    return show("ok", `Расширение стоит (${esc(version)}) и подключено к аккаунту <b>${esc(me.login)}</b> ✓ Переходи к шагу 6.`);
  }
  if (status.login) {
    return show("missing", `Расширение подключено к другому аккаунту — <b>${esc(status.login)}</b>: заказы уходят туда.`,
      `Подключить к ${me.login}`);
  }
  show("missing", `Расширение стоит (${esc(version)}), осталось подключить его к аккаунту <b>${esc(me.login)}</b>.`,
    "Подключить расширение");
}

connectBtn.addEventListener("click", async () => {
  connectBtn.disabled = true;
  connectBtn.textContent = "Подключаю…";
  const result = await askExtension("extension-connect", 15000);
  connectBtn.disabled = false;
  if (result && !result.error) return checkExtension();
  show("missing", `Не получилось подключить: ${esc(result ? result.error : "расширение не ответило")}.`, "Попробовать ещё раз");
});

document.querySelectorAll("[data-copy], [data-copy-from]").forEach((button) => button.addEventListener("click", async () => {
  const input = button.dataset.copyFrom ? document.getElementById(button.dataset.copyFrom) : button.previousElementSibling;
  const text = button.dataset.copy || input.value;
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Скопировано ✓";
    setTimeout(() => { button.textContent = "Скопировать"; }, 2500);
  } catch (_) {
    input.select(); // the clipboard needs https or localhost
  }
}));

// The connector's address and command on this very site (eaty.lol in prod, localhost locally).
const mcpUrl = `${location.origin}/mcp`;
document.getElementById("mcp-url").value = mcpUrl;
document.getElementById("mcp-cli").value = `claude mcp add --transport http eaty ${mcpUrl}`;

(async () => {
  me = await signedIn();
  if (me) {
    document.getElementById("me-status").innerHTML = `Аккаунт в eaty: вход как <b>${esc(me.login)}</b> ✓`;
    document.querySelector('[data-check="me"]').textContent = "✅";
  }
  checkExtension();
})();
