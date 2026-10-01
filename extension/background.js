// Sends orders to the eaty app. The app URL is set on the extension's popup.
"use strict";

const DEFAULT_APP_URL = "http://localhost:8080";

async function appUrl() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return appUrl.replace(/\/+$/, "");
}

async function deliver(orders, path, source) {
  const status = { at: new Date().toISOString(), path, source, orders: orders.length };
  try {
    const url = await appUrl();
    status.url = url;
    const resp = await fetch(`${url}/api/v1/wolt-orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orders }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${(await resp.text()).slice(0, 300)}`);
    Object.assign(status, { ok: true, result: await resp.json() });
  } catch (err) {
    Object.assign(status, { ok: false, error: String(err.message || err) });
  }
  await chrome.storage.local.set({ lastSync: status });
}

// What the extension looked at on wolt.com, for the popup: the last few responses and pages
// and whether an order was found there; the shape of the last one where nothing was found.
async function remember({ path, source, orders, shape }) {
  const { seen = [] } = await chrome.storage.local.get("seen");
  const update = { seen: [{ at: new Date().toISOString(), path, source, orders }, ...seen].slice(0, 10) };
  if (shape) update.lastShape = { path, shape };
  await chrome.storage.local.set(update);
}

let remembering = Promise.resolve(); // one at a time: each call reads and rewrites the list

chrome.runtime.onMessage.addListener((message) => {
  if (message && message.type === "orders" && Array.isArray(message.orders)) {
    deliver(message.orders, message.path, message.source);
  } else if (message && message.type === "seen") {
    remembering = remembering.then(() => remember(message)).catch(() => {});
  }
});
