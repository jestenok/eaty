// Sends orders to the eaty app. The app URL and the sign-in are set on the extension's popup.
"use strict";

const DEFAULT_APP_URL = "http://localhost:8080";

async function appUrl() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return appUrl.replace(/\/+$/, "");
}

async function deliver(orders, path) {
  const status = { at: new Date().toISOString(), path, orders: orders.length };
  try {
    // The token is the extension's own sign-in (popup.js); the app's cookies aren't used.
    const { token } = await chrome.storage.local.get({ token: null });
    if (!token) throw new Error("не выполнен вход: открой окошко расширения и войди");
    const resp = await fetch(`${await appUrl()}/api/v1/wolt-orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ orders }),
    });
    if (resp.status === 401) throw new Error("вход истёк: войди заново в окошке расширения");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    Object.assign(status, { ok: true, result: await resp.json() });
  } catch (err) {
    Object.assign(status, { ok: false, error: String(err.message || err) });
  }
  await chrome.storage.local.set({ lastSync: status });
}

chrome.runtime.onMessage.addListener((message) => {
  if (message && message.type === "orders" && Array.isArray(message.orders)) {
    deliver(message.orders, message.path);
  }
});
