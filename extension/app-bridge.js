// Runs on the eaty app's pages. Lets the app see that the extension is installed and ask
// it to sync orders from Wolt; also tells the extension where the app lives, so it sends
// orders there without manual setup.
(function () {
  "use strict";
  document.documentElement.dataset.eatyExtension = chrome.runtime.getManifest().version;
  chrome.runtime.sendMessage({ type: "hello", origin: location.origin });

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.source !== "eaty-app" || data.type !== "wolt-sync") return;
    chrome.runtime.sendMessage({ type: "sync", origin: location.origin }, (result) => {
      const error = chrome.runtime.lastError ? chrome.runtime.lastError.message : null;
      window.postMessage({ source: "eaty-extension", type: "wolt-sync-result", result: result || { error } },
        location.origin);
    });
  });
})();
