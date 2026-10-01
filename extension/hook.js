// Runs in the page (MAIN world). Watches JSON responses that wolt.com itself requests
// and passes found orders to content.js. Request headers are never read or sent anywhere.
(function () {
  "use strict";
  const { findOrders } = window.EatyExtract;
  const WATCH = /order/i;            // order history, order details, tracking
  const SKIP = /basket|cart|checkout|auth|token|login/i;

  function shouldWatch(url) {
    try {
      const u = new URL(url, location.href);
      return /(^|\.)wolt\.com$/.test(u.hostname) && WATCH.test(u.pathname) && !SKIP.test(u.pathname);
    } catch (_) {
      return false;
    }
  }

  function inspect(url, json) {
    const orders = findOrders(json);
    if (orders.length) {
      const path = new URL(url, location.href).pathname; // no query string
      window.postMessage({ source: "eaty-hook", orders, path }, location.origin);
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
