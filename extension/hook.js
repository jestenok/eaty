// Runs in the page (MAIN world), where all of the order finding happens: it watches JSON
// responses that wolt.com itself requests, looks into the data embedded into order pages, and
// as a last resort reads the order off the order page once it has rendered. Findings go to
// content.js, which passes them on. Request headers are never read or sent anywhere.
//
// extract.js is injected into this world only: Chrome injects a file listed in two
// content_scripts entries into just one of the worlds, so content.js must not depend on it.
(function () {
  "use strict";
  const { findOrders, shapeOf, findOrderInPage, orderIdFromPath } = window.EatyExtract;
  const WATCH = /order|purchase|receipt/i; // order history, order details, tracking
  const SKIP = /basket|cart|checkout|auth|token|login/i;
  const fromData = new Map(); // order id -> number of items, for orders found in Wolt's data on this tab

  function post(message) {
    window.postMessage({ eaty: "hook", message }, location.origin);
  }

  function report(orders, path, source, shape) {
    post({ type: "seen", path, source, orders: orders.length, shape: shape || null });
    if (!orders.length) return;
    if (source !== "page") orders.forEach((o) => fromData.set(o.id, Math.max(o.items.length, fromData.get(o.id) || 0)));
    post({ type: "orders", orders, path, source });
  }

  // ---- JSON that wolt.com loads ----

  function shouldWatch(url) {
    try {
      const u = new URL(url, location.href);
      const path = u.pathname.replace(/order-xp/gi, ""); // a prefix of most consumer-api paths, menus too
      return /(^|\.)wolt\.com$/.test(u.hostname) && WATCH.test(path) && !SKIP.test(path);
    } catch (_) {
      return false;
    }
  }

  // Every watched response is reported, so the popup can show what was looked at. When no
  // order is recognized, only the shape of the response (keys and types) goes along.
  function inspect(url, json) {
    const orders = findOrders(json);
    const path = new URL(url, location.href).pathname; // no query string
    report(orders, path, "json", orders.length ? null : JSON.stringify(shapeOf(json)).slice(0, 20000));
  }

  const originalFetch = window.fetch;
  window.fetch = async function (input, init) {
    const response = await originalFetch.apply(this, arguments);
    try {
      const url = typeof input === "string" ? input : input && input.url;
      if (url && shouldWatch(url) && (response.headers.get("content-type") || "").includes("json")) {
        response.clone().json().then((json) => inspect(url, json)).catch(() => {});
      }
    } catch (_) { /* never break the page */ }
    return response;
  };

  const open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    this.__eatyUrl = url;
    return open.apply(this, arguments);
  };
  const send = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function () {
    if (this.__eatyUrl && shouldWatch(this.__eatyUrl)) {
      this.addEventListener("load", () => {
        try {
          const json = this.responseType === "json" ? this.response : JSON.parse(this.responseText);
          inspect(this.__eatyUrl, json);
        } catch (_) { /* not json */ }
      });
    }
    return send.apply(this, arguments);
  };

  // ---- Data embedded into the page when it's rendered on the server ----

  function scanEmbedded() {
    if (!/order/i.test(location.pathname)) return;
    for (const script of document.querySelectorAll('script[type="application/json"]')) {
      try {
        const orders = findOrders(JSON.parse(script.textContent));
        if (orders.length) report(orders, location.pathname, "embedded");
      } catch (_) { /* not json */ }
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scanEmbedded);
  else scanEmbedded();

  // ---- The order page itself, once the DOM settles ----

  let lastPage = "";
  function scanPage() {
    const id = orderIdFromPath(location.pathname);
    if (!id) return;
    const order = findOrderInPage(document, location.pathname);
    // Wolt's data wins, unless the page shows more items (history may list only the first few).
    if (fromData.has(id) && (!order || order.items.length <= fromData.get(id))) return;
    const key = order ? `${order.id}:${order.items.map((i) => `${i.name}×${i.count}`).join("|")}` : `${id}:none`;
    if (key === lastPage) return;
    lastPage = key;
    report(order ? [order] : [], location.pathname, "page");
  }

  // Waits for the page to settle, but not forever if something on it keeps changing.
  let timer = null;
  let since = 0;
  new MutationObserver(() => {
    if (!orderIdFromPath(location.pathname)) return;
    clearTimeout(timer);
    since = since || Date.now();
    timer = setTimeout(() => { since = 0; scanPage(); }, Date.now() - since > 3000 ? 0 : 800);
  }).observe(document, { subtree: true, childList: true, characterData: true });
})();
