// Isolated world: relays orders from hook.js to the background worker, and also looks
// into the data wolt.com embeds into order pages when they are rendered on the server.
(function () {
  "use strict";
  const { findOrders } = globalThis.EatyExtract;

  function send(orders, path) {
    if (orders.length) chrome.runtime.sendMessage({ type: "orders", orders, path });
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (data && data.source === "eaty-hook" && Array.isArray(data.orders)) send(data.orders, data.path);
  });

  function scanEmbedded() {
    if (!/order/i.test(location.pathname)) return;
    for (const script of document.querySelectorAll('script[type="application/json"]')) {
      try {
        send(findOrders(JSON.parse(script.textContent)), location.pathname);
      } catch (_) { /* not json */ }
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scanEmbedded);
  else scanEmbedded();
})();
