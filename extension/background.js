// Sends orders to the eaty app and runs syncs started from the app.
"use strict";

const DEFAULT_APP_URL = "http://localhost:8080";
const ORDER_HISTORY = "https://wolt.com/ru/me/order-history#eaty-sync";
const DEFAULT_DAYS = 7;
const SYNC_TIMEOUT_MS = 120000;
const pending = new Map(); // tab id -> resolve of a running sync

async function appUrl() {
  const { appUrl } = await chrome.storage.sync.get({ appUrl: DEFAULT_APP_URL });
  return appUrl.replace(/\/+$/, "");
}

// The app announces itself when opened; remember it unless the address was set by hand.
async function rememberApp(origin) {
  const { appUrlManual } = await chrome.storage.sync.get({ appUrlManual: false });
  if (!appUrlManual) await chrome.storage.sync.set({ appUrl: origin });
}

async function post(base, path, body) {
  const resp = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${(await resp.text()).slice(0, 200)}`);
  return resp.json();
}

async function deliver(orders, path) {
  const status = { at: new Date().toISOString(), path, orders: orders.length };
  try {
    Object.assign(status, { ok: true, result: await post(await appUrl(), "/api/v1/wolt-orders", { orders }) });
  } catch (err) {
    Object.assign(status, { ok: false, error: String(err.message || err) });
  }
  await chrome.storage.local.set({ lastSync: status });
}

async function runSync(origin, days) {
  const tab = await chrome.tabs.create({ url: `${ORDER_HISTORY}&days=${days}`, active: false });
  const result = await new Promise((resolve) => {
    pending.set(tab.id, resolve);
    setTimeout(() => {
      if (pending.delete(tab.id)) resolve({ orders: [], diagnostics: { error: "timeout" } });
    }, SYNC_TIMEOUT_MS);
  });
  chrome.tabs.remove(tab.id).catch(() => {});

  const summary = { source: "button", orders_found: result.orders.length, orders_imported: 0, pantry_items: 0, error: null };
  if (result.orders.length) {
    try {
      const imported = await post(origin, "/api/v1/wolt-orders", { orders: result.orders });
      Object.assign(summary, {
        orders_imported: imported.orders, pantry_items: imported.pantry_items,
        skipped: { restaurants: imported.skipped_restaurants, unknown: imported.skipped_unknown, old: imported.skipped_old },
      });
    } catch (err) {
      summary.error = String(err.message || err);
    }
  } else {
    summary.error = result.diagnostics && result.diagnostics.error === "timeout"
      ? "Wolt не ответил за 2 минуты"
      : `За последние ${days} дн. в истории заказов не нашлось ни одного заказа, который получилось разобрать`;
  }
  // The summary (with what the extension saw on wolt.com) is kept by the app for diagnostics.
  const { skipped, ...log } = summary;
  try { await post(origin, "/api/v1/wolt-orders/sync-log", { ...log, details: { ...result.diagnostics, skipped } }); } catch (_) { /* best effort */ }
  await chrome.storage.local.set({
    lastSync: { at: new Date().toISOString(), ok: !summary.error, error: summary.error,
                result: { orders: summary.orders_imported, pantry_items: summary.pantry_items } },
  });
  return summary;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) return;
  if (message.type === "orders" && Array.isArray(message.orders)) deliver(message.orders, message.path);
  if (message.type === "hello" && message.origin) rememberApp(message.origin);
  if (message.type === "sync" && message.origin) {
    runSync(message.origin, message.days || DEFAULT_DAYS).then(sendResponse, (err) => sendResponse({ error: String(err.message || err) }));
    return true; // the answer comes later
  }
  if (message.type === "sync-result" && sender.tab && pending.has(sender.tab.id)) {
    pending.get(sender.tab.id)(message);
    pending.delete(sender.tab.id);
  }
});
