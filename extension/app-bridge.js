// Runs on the eaty app's pages. Lets the app see that the extension is installed, ask it to
// sync orders from Wolt, ask who it is signed in as and sign it in as whoever is signed in on
// the page; also tells the extension where the app lives, so it sends orders there without
// manual setup. Each request "x" from the page is answered with "x-result".
(function () {
  "use strict";
  document.documentElement.dataset.eatyExtension = chrome.runtime.getManifest().version;
  chrome.runtime.sendMessage({ type: "hello", origin: location.origin });

  const ask = (message) => chrome.runtime.sendMessage({ ...message, origin: location.origin });

  // The sign-in is taken with the page's cookie right here, in the extension's own world, so
  // its token never passes through the page: the page only learns the login.
  async function connect() {
    const resp = await fetch(`${location.origin}/api/v1/auth/extension-token`, { method: "POST" });
    if (resp.status === 401) return { error: "на сайте не выполнен вход" };
    if (!resp.ok) return { error: `ответ ${resp.status}` };
    const { token, user } = await resp.json();
    return ask({ type: "signin", token, login: user.login });
  }

  const handlers = {
    "wolt-sync": (data) => ask({ type: "sync", days: data.days }),
    "extension-status": () => ask({ type: "status" }),
    "extension-connect": connect,
  };

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.source !== "eaty-app" || !Object.hasOwn(handlers, data.type)) return;
    handlers[data.type](data)
      .catch((err) => ({ error: String(err.message || err) }))
      .then((result) => window.postMessage(
        { source: "eaty-extension", type: `${data.type}-result`, result: result || {} }, location.origin));
  });
})();
