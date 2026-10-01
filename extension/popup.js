"use strict";

const DEFAULT_APP_URL = "http://localhost:8080";
const urlInput = document.getElementById("url");
const signinForm = document.getElementById("signin");
const accountEl = document.getElementById("account");
const statusEl = document.getElementById("status");
const lastEl = document.getElementById("last");

function show(el, text, cls) {
  el.textContent = text;
  el.className = cls || "muted";
}

function base() {
  return (urlInput.value.trim() || DEFAULT_APP_URL).replace(/\/+$/, "");
}

// The sign-in token lives in local storage (not synced to other computers).
async function showAccount() {
  const { token, login } = await chrome.storage.local.get({ token: null, login: "" });
  signinForm.hidden = !!token;
  accountEl.hidden = !token;
  document.getElementById("who").textContent = login;
  return token;
}

async function load() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  urlInput.value = appUrl;
  await showAccount();
  const { lastSync } = await chrome.storage.local.get("lastSync");
  if (lastSync) {
    const when = new Date(lastSync.at).toLocaleString("ru-RU");
    if (lastSync.ok) show(lastEl, `Последняя отправка ${when}: заказов ${lastSync.result.orders}, в «Дома» ${lastSync.result.pantry_items}.`, "ok");
    else show(lastEl, `Последняя отправка ${when} не удалась: ${lastSync.error}`, "err");
  }
}

document.getElementById("save").addEventListener("click", async () => {
  await chrome.storage.sync.set({ appUrl: base() });
  show(statusEl, "Сохранено.", "ok");
});

signinForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const login = document.getElementById("login").value.trim();
  const password = document.getElementById("password").value;
  if (!login || !password) return show(statusEl, "Впиши логин и пароль от eaty.", "err");
  try {
    const resp = await fetch(`${base()}/api/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login, password }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(typeof data.detail === "string" ? data.detail : `ответ ${resp.status}`);
    await chrome.storage.sync.set({ appUrl: base() });
    await chrome.storage.local.set({ token: data.token, login: data.user.login });
    document.getElementById("password").value = "";
    await showAccount();
    show(statusEl, "Вошли ♡ Открой заказ на wolt.com ещё раз, чтобы он попал в «Дома».", "ok");
  } catch (err) {
    show(statusEl, `Не получилось войти: ${err.message}`, "err");
  }
});

document.getElementById("signout").addEventListener("click", async () => {
  const { token } = await chrome.storage.local.get({ token: null });
  try {
    await fetch(`${base()}/api/v1/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
  } catch (_) { /* the token is forgotten here anyway */ }
  await chrome.storage.local.remove(["token", "login"]);
  await showAccount();
  show(statusEl, "Вышли.", "muted");
});

document.getElementById("check").addEventListener("click", async () => {
  const token = await showAccount();
  try {
    const resp = await fetch(`${base()}/api/v1/auth/me`, token ? { headers: { Authorization: `Bearer ${token}` } } : {});
    if (resp.ok) return show(statusEl, `Приложение на связи, вход: ${(await resp.json()).login} ♡`, "ok");
    if (resp.status === 401) return show(statusEl, token ? "Приложение на связи, но вход истёк: войди заново." : "Приложение на связи. Войди, чтобы заказы попадали в твой аккаунт.", "err");
    show(statusEl, `Ответ ${resp.status}`, "err");
  } catch (err) {
    show(statusEl, `Не достучаться: ${err.message}. Приложение запущено?`, "err");
  }
});

load();
