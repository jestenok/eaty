// Isolated world: passes what hook.js found in the page on to the background worker. Pages
// can't reach chrome.runtime, content scripts can. Self-contained on purpose: see hook.js.
(function () {
  "use strict";

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data && event.data.eaty === "hook" ? event.data.message : null;
    if (!message || typeof message.path !== "string") return;
    if ((message.type === "orders" && Array.isArray(message.orders)) || message.type === "seen") {
      chrome.runtime.sendMessage(message);
    }
  });
})();
