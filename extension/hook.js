// Runs in the page (MAIN world). Watches JSON responses that wolt.com itself requests
// and passes found orders to content.js. Request headers are never read or sent anywhere.
//
// Normally only order-looking URLs are inspected. During a sync started from the eaty app
// ("capture-all") every wolt.com JSON response is inspected, and a summary of what was seen
// (path, top-level field names, how many orders were found — no values) goes along, so a
// change in Wolt's format can be diagnosed without anyone browsing the account.
(function () {
  "use strict";
  const { findOrders } = window.EatyExtract;
  const WATCH = /order|purchase/i;
  const SKIP = /basket|cart|checkout|auth|token|login|payment-method/i;
  let captureAll = false;

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    if (event.data && event.data.source === "eaty-content" && event.data.type === "capture-all") captureAll = true;
  });

  function shouldWatch(url) {
    try {
      const u = new URL(url, location.href);
      return /(^|\.)wolt\.com$/.test(u.hostname) && !SKIP.test(u.pathname) && (captureAll || WATCH.test(u.pathname));
    } catch (_) {
      return false;
    }
  }

  function inspect(url, json) {
    const orders = findOrders(json);
    const path = new URL(url, location.href).pathname; // no query string
    if (orders.length) window.postMessage({ source: "eaty-hook", orders, path }, location.origin);
    if (captureAll) {
      const keys = json && typeof json === "object" && !Array.isArray(json) ? Object.keys(json).slice(0, 20) : ["<array>"];
      window.postMessage({ source: "eaty-hook", type: "diag", entry: { path, keys, orders: orders.length } }, location.origin);
    }
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
})();
