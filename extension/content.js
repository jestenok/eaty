// Isolated world on wolt.com. Two modes:
// - passive: relays orders hook.js saw while you browse, and orders embedded into
//   server-rendered order pages, to the background worker;
// - sync (the tab was opened by the "Обновить из Wolt" button, URL hash #eaty-sync):
//   opens the latest orders on the order-history page one by one so wolt.com loads their
//   details, collects them and reports back with a summary of what was seen.
(function () {
  "use strict";
  const { findOrders } = globalThis.EatyExtract;
  const SYNC = location.hash.includes("eaty-sync");
  const MAX_ORDERS = 8;
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

  function send(orders, path) {
    if (!orders.length) return;
    if (SYNC) orders.forEach((o) => collected.set(o.id, o));
    else chrome.runtime.sendMessage({ type: "orders", orders, path });
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.source !== "eaty-hook") return;
    if (data.type === "diag") responses.push(data.entry);
    else if (Array.isArray(data.orders)) send(data.orders, data.path);
  });

  function scanEmbedded() {
    if (!/order/i.test(location.pathname)) return;
    for (const script of document.querySelectorAll('script[type="application/json"]')) {
      try {
        send(findOrders(JSON.parse(script.textContent)), location.pathname);
      } catch (_) { /* not json */ }
    }
  }

  // ---------- sync ----------

  const ORDER_ROW = /\d{2}\.\d{2}\.\d{4}/;      // order rows show the date: 01.10.2026, 12:16
  const PRIVATE_LINE = /\+?\d[\d\s()-]{8,}|street|улиц|ул\.|просп|проезд|кв\.|подъезд|этаж|entrance|floor|apartment|@/i;

  function orderRows() {
    return [...document.querySelectorAll("main button, main a, main [role=button]")]
      .filter((el) => ORDER_ROW.test(el.innerText || "") && (el.innerText || "").length < 200);
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
    const rows = (await waitFor(() => orderRows().length && orderRows(), 20000)) || [];
    const sketches = [];
    for (const row of rows.slice(0, MAX_ORDERS)) {
      row.scrollIntoView({ block: "center" });
      row.click();
      const dialog = await waitFor(() => document.querySelector("[role=dialog]"), 8000);
      await sleep(2000); // let the details request finish
      if (dialog && sketches.length < 2) sketches.push(dialogSketch(dialog));
      closeDialog();
      await sleep(700);
    }
    scanEmbedded();
    await sleep(1000);
    const orders = [...collected.values()];
    chrome.runtime.sendMessage({
      type: "sync-result",
      orders,
      diagnostics: {
        page: location.pathname,
        logged_in: !/login|signin/i.test(location.pathname),
        order_rows: rows.length,
        opened: Math.min(rows.length, MAX_ORDERS),
        responses: responses.slice(0, 80),
        dialogs: orders.length ? [] : sketches,
      },
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => (SYNC ? runSync() : scanEmbedded()));
  else if (SYNC) runSync();
  else scanEmbedded();
})();
