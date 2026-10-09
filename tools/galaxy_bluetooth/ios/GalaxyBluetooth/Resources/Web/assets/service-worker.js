self.addEventListener("install", () => self.skipWaiting())
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()))

const appBasePath = self.location.pathname.replace(/\/service-worker\.js$/, "").replace(/\/$/, "")

function scopedUrl(path) {
  const url = new URL(path || "/sentry", self.location.origin)
  if (appBasePath && url.pathname !== appBasePath && !url.pathname.startsWith(`${appBasePath}/`)) {
    url.pathname = `${appBasePath}${url.pathname}`
  }
  return url.href
}

self.addEventListener("push", (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { body: event.data?.text() || "Sentry event detected." }
  }

  const title = data.title || "StarPilot Sentry Mode"
  const options = {
    body: data.body || "Movement detected while parked.",
    tag: `starpilot-sentry-${data.eventId || "event"}`,
    data: { url: scopedUrl(data.url || "/sentry") },
    icon: scopedUrl("/assets/images/favicon.ico"),
    badge: scopedUrl("/assets/images/favicon-32x32.png"),
    requireInteraction: true,
  }
  if (data.image) options.image = scopedUrl(data.image)

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener("notificationclick", (event) => {
  event.notification.close()
  const targetUrl = scopedUrl(event.notification.data?.url || "/sentry")

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if ("focus" in client) {
          client.navigate(targetUrl)
          return client.focus()
        }
      }
      return clients.openWindow(targetUrl)
    })
  )
})
