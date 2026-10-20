self.addEventListener("push", event => {
  event.waitUntil((async () => {
    let value
    try { value = event.data.json() } catch { value = {} }
    const id = typeof value?.eventId === "string" && /^[0-9a-f]{32}$/.test(value.eventId) ? value.eventId : "sentry"
    const body = typeof value?.body === "string" ? value.body.slice(0, 256) : "Parked motion detected."
    await self.registration.showNotification("StarPilot Sentry Mode", { body, tag: id,
      data: { url: new URL("./#/cameras/events", self.registration.scope).href } })
  })())
})
self.addEventListener("notificationclick", event => {
  event.notification.close()
  event.waitUntil((async () => {
    const url = new URL("./#/cameras/events", self.registration.scope).href
    const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true })
    const existing = windows.find(client => client.url.startsWith(self.registration.scope))
    if (existing) { await existing.navigate(url); return existing.focus() }
    return self.clients.openWindow(url)
  })())
})

// Migrate away from the legacy downloaded app shell without unregistering push.
self.addEventListener("install", () => self.skipWaiting())
self.addEventListener("activate", event => event.waitUntil((async () => {
  await caches.delete("galaxy-offline-v1")
  await self.clients.claim()
})()))
