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

  // Badge del icono de la app (Android/desktop instalada e iOS ≥16.4).
  // Solo se toca si el aviso TRAE `count`: sin él no sabemos cuántos pendientes
  // hay, y tratar su ausencia como cero apagaba el contador (p. ej. los "pagos
  // sin leer" del coach) sin que se hubiera leído nada.
  if ("setAppBadge" in self.navigator && data.count !== undefined && data.count !== null) {
    const count = Number(data.count) || 0;
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
      // La notificación manda a SU url (Meet, pestaña del coach…): solo se
      // reutiliza una ventana si ya está EN esa url. Antes se enfocaba
      // cualquier pestaña con /p/ y el aviso nunca llegaba a su destino
      // (p. ej. el enlace de Meet, o el perfil del cliente en la web del coach).
      for (const win of wins) {
        if (win.url === url && "focus" in win) return win.focus();
      }
      // Ventana del MISMO portal abierta y el aviso apunta al portal: navegar
      // esa ventana a la url del aviso en vez de abrir otra.
      for (const win of wins) {
        if (url.includes("/p/") && win.url.includes("/p/") && "navigate" in win) {
          return win.navigate(url).then((w) => (w && "focus" in w ? w.focus() : undefined));
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
