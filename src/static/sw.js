"use strict";

// eaty's service worker: shows the server's pushes — «Готово!» when a step's timer is up, even with
// the phone locked and eaty closed. No caching: the app always comes from the server.

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (_) { data = { body: event.data.text() }; }
  // a push must show a notification: an iPhone stops delivering pushes to apps that keep quiet
  event.waitUntil(self.registration.showNotification(data.title || "eaty", {
    body: data.body || "",
    tag: data.tag,                 // one notification per timer, a new one replaces it
    renotify: true,                // …and still rings
    requireInteraction: true,      // stays until tapped, where the browser lets it
    icon: "/static/icons/icon-192.png",
    data: { url: data.url || "/" },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL(event.notification.data.url || "/", self.location.origin).href;
  event.waitUntil((async () => {
    const open = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    const app = open.find((c) => new URL(c.url).origin === self.location.origin);
    if (app) {
      await app.focus();
      if (app.url !== url && "navigate" in app) await app.navigate(url).catch(() => {});
    } else {
      await self.clients.openWindow(url);
    }
  })());
});
