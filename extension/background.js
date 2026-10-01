// Sends orders to the eaty app. The app URL is set on the extension's popup.
"use strict";

const DEFAULT_APP_URL = "http://localhost:8000";

async function appUrl() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return appUrl.replace(/\/+$/, "");
}

async function deliver(orders, path) {
  const status = { at: new Date().toISOString(), path, orders: orders.length };
  try {
    const resp = await fetch(`${await appUrl()}/api/wolt/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orders }),
    });
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
