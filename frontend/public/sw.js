/* Service worker del portal — Web Push + badge (TRASPASO §8.1).
 *
 * Servido desde la raíz (/sw.js) para que su scope cubra /p/{token}. No hace
 * caché offline: su único trabajo es recibir pushes, mostrarlos y mantener el
 * numerito (badge) del icono de la app instalada.
 *
 * El payload que envía el backend (services/push.py) es JSON:
 *   { title, body, count, url, tag }
 */

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { body: event.data ? event.data.text() : "" };
  }

  const title = data.title || "Tu seguimiento";
  const count = Number(data.count) || 0;

  const tasks = [
    self.registration.showNotification(title, {
      body: data.body || "Tienes registros pendientes de hoy.",
      icon: "/icons/icon-192.png",
      badge: "/icons/badge-72.png", // Android: icono monocromo de la barra
      tag: data.tag || "dq-seguimiento", // misma tag → sustituye a la anterior
      renotify: true, // que vuelva a sonar/vibrar aunque sustituya
      data: { url: data.url || "/" },
    }),
  ];

  // Badge del icono de la app (Android/desktop instalada e iOS ≥16.4)
  if ("setAppBadge" in self.navigator) {
    tasks.push(
      count > 0 ? self.navigator.setAppBadge(count) : self.navigator.clearAppBadge()
    );
  }

  event.waitUntil(Promise.all(tasks));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
      // Si el portal ya está abierto en alguna pestaña/app, enfocarla
      for (const win of wins) {
        if (win.url.includes("/p/") && "focus" in win) return win.focus();
      }
      return self.clients.openWindow(url);
    })
  );
});
