// Isolated world on wolt.com: passes what hook.js found in the page on to the background
// worker (pages can't reach chrome.runtime, content scripts can). Self-contained on purpose:
// see hook.js. Two modes:
// - passive: relays orders hook.js found while you browse;
// - sync (the tab was opened by the "Обновить из Wolt" button, URL hash #eaty-sync):
//   opens the latest orders on the order-history page one by one so wolt.com loads their
//   details, collects what hook.js finds and reports back with a summary of what was seen.
(function () {
  "use strict";
  const SYNC = location.hash.includes("eaty-sync");
  const DAYS = Number((location.hash.match(/days=(\d+)/) || [])[1] || 7);
  const MAX_ORDERS = 15;
  const collected = new Map();
  const responses = [];

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function waitFor(fn, ms) {
    const until = Date.now() + ms;
    while (Date.now() < until) {
      const value = fn();
      if (value) return value;
      await sleep(250);
    }
    return null;
  }

  // The same order may come from Wolt's data and from the page: keep the fuller one.
  function collect(orders) {
    for (const o of orders) {
      const had = collected.get(o.id);
      if (!had || o.items.length >= had.items.length) collected.set(o.id, o);
    }
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data && event.data.eaty === "hook" ? event.data.message : null;
    if (!message) return;
    if (message.type === "diag") {
      if (SYNC && message.entry) responses.push(message.entry);
      return;
    }
    if (typeof message.path !== "string") return;
    if (message.type === "orders" && Array.isArray(message.orders)) {
      if (SYNC) collect(message.orders);
      else chrome.runtime.sendMessage(message);
    } else if (message.type === "seen") {
      chrome.runtime.sendMessage(message);
    }
  });

  // ---------- sync ----------

  const ORDER_ROW = /(\d{2})\.(\d{2})\.(\d{4})/;   // order rows show the date: 01.10.2026, 12:16
  const PRIVATE_LINE = /\+?\d[\d\s()-]{8,}|street|улиц|ул\.|просп|проезд|кв\.|подъезд|этаж|entrance|floor|apartment|@/i;

  function orderRows() {
    return [...document.querySelectorAll("main button, main a, main [role=button]")]
      .filter((el) => ORDER_ROW.test(el.innerText || "") && (el.innerText || "").length < 200);
  }

  // Only orders of the last DAYS days: older food is long eaten.
  function isRecent(row) {
    const [, d, m, y] = (row.innerText || "").match(ORDER_ROW);
    const oldest = new Date();
    oldest.setHours(0, 0, 0, 0);
    oldest.setDate(oldest.getDate() - DAYS);
    return new Date(+y, +m - 1, +d) >= oldest;
  }

  function closeDialog() {
    const close = [...document.querySelectorAll("[role=dialog] button[aria-label]")]
      .find((b) => /закры|close/i.test(b.getAttribute("aria-label")));
    if (close) close.click();
    else document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  }

  // What an opened order looks like on screen, without addresses and phones: used only when
  // no order could be parsed from the data, to fix the parser.
  function dialogSketch(dialog) {
    return (dialog.innerText || "").split("\n").map((l) => l.trim())
      .filter((l) => l && !PRIVATE_LINE.test(l)).slice(0, 60).map((l) => l.slice(0, 100));
  }

  async function runSync() {
    window.postMessage({ source: "eaty-content", type: "capture-all" }, location.origin);
    const allRows = (await waitFor(() => orderRows().length && orderRows(), 20000)) || [];
    const rows = allRows.filter(isRecent);
    const sketches = [];
    for (const row of rows.slice(0, MAX_ORDERS)) {
      row.scrollIntoView({ block: "center" });
      row.click();
      const dialog = await waitFor(() => document.querySelector("[role=dialog]"), 8000);
      await sleep(2500); // let the details request finish and the page settle for hook.js
      if (dialog && sketches.length < 2) sketches.push(dialogSketch(dialog));
      closeDialog();
      await sleep(700);
    }
    await sleep(1000);
    const orders = [...collected.values()];
    chrome.runtime.sendMessage({
      type: "sync-result",
      orders,
      diagnostics: {
        page: location.pathname,
        logged_in: !/login|signin/i.test(location.pathname),
        days: DAYS,
        order_rows: allRows.length,
        recent_rows: rows.length,
        opened: Math.min(rows.length, MAX_ORDERS),
        responses: responses.slice(0, 80),
        dialogs: orders.length ? [] : sketches,
      },
    });
  }

  if (SYNC) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", runSync);
    else runSync();
  }
})();
