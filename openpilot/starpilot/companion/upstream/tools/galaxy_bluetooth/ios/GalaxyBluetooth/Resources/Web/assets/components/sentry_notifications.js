import { galaxyPath } from "/assets/js/utils.js"

const STORAGE_KEY = "starpilot.sentry.last-event"
const POLL_INTERVAL_MS = 5000
const SERVICE_WORKER_PATH = "/service-worker.js"

let started = false
let initialized = false

function lastSeenEventId() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) || ""
  } catch {
    return ""
  }
}

function rememberEvent(eventId) {
  try {
    window.localStorage.setItem(STORAGE_KEY, eventId)
  } catch {
  }
}

async function pollSentryEvent() {
  try {
    const response = await fetch(galaxyPath("/api/sentry/status"), { cache: "no-store" })
    if (!response.ok) return
    const payload = await response.json()
    const event = payload?.lastEvent
    const eventId = String(event?.eventId || "")
    if (!eventId) return

    const previous = lastSeenEventId()
    rememberEvent(eventId)
    if (!initialized || eventId === previous) return
    if (typeof Notification === "undefined" || Notification.permission !== "granted") return

    new Notification("StarPilot Sentry Mode", {
      body: String(event.message || "Movement detected while parked."),
      tag: `starpilot-sentry-${eventId}`,
    })
  } catch (error) {
    console.debug("Sentry notification poll failed:", error)
  } finally {
    initialized = true
  }
}

export async function requestSentryNotificationPermission() {
  if (typeof Notification === "undefined") return "unsupported"
  return Notification.requestPermission()
}

function base64ToUint8Array(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4)
  const normalized = (value + padding).replace(/-/g, "+").replace(/_/g, "/")
  const raw = window.atob(normalized)
  return Uint8Array.from(raw, (character) => character.charCodeAt(0))
}

function subscriptionPayload(subscription) {
  if (typeof subscription.toJSON === "function") return subscription.toJSON()

  const key = (name) => subscription.getKey(name)
  const encode = (value) => btoa(String.fromCharCode(...new Uint8Array(value)))
  return {
    endpoint: subscription.endpoint,
    expirationTime: subscription.expirationTime,
    keys: {
      p256dh: encode(key("p256dh")),
      auth: encode(key("auth")),
    },
  }
}

async function readJsonResponse(response) {
  const body = await response.text()
  if (!body) return {}

  try {
    return JSON.parse(body)
  } catch {
    const contentType = response.headers?.get("content-type") || ""
    if (contentType.includes("text/html") || body.trim().startsWith("<")) {
      if (response.status === 200) {
        throw new Error("Galaxy returned an HTML page instead of JSON data. Check your session or connection.")
      }
      throw new Error(`Galaxy returned an HTML error page (${response.status}). Check the device connection or Galaxy tunnel.`)
    }
    throw new Error(`Galaxy returned an unexpected ${response.status} response. Check the device connection or Galaxy tunnel.`)
  }
}

export async function enableSentryPush() {
  if (typeof Notification === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
    return { ok: false, message: "This browser does not support Web Push notifications." }
  }
  if (!window.isSecureContext) {
    return { ok: false, message: "Browser notifications require Galaxy over HTTPS." }
  }

  const permission = await requestSentryNotificationPermission()
  if (permission !== "granted") {
    return { ok: false, message: "Browser notification permission was not granted." }
  }

  const configResponse = await fetch(galaxyPath("/api/sentry/push/config"), { cache: "no-store" })
  const config = await readJsonResponse(configResponse)
  if (!configResponse.ok || !config.enabled || !config.publicKey) {
    return { ok: false, message: config.error || "Galaxy Web Push is unavailable." }
  }

  const serviceWorkerPath = galaxyPath(SERVICE_WORKER_PATH)
  const serviceWorkerScope = galaxyPath("/")
  await navigator.serviceWorker.register(serviceWorkerPath, { scope: serviceWorkerScope })
  const registration = await navigator.serviceWorker.ready
  let subscription = await registration.pushManager.getSubscription()
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64ToUint8Array(config.publicKey),
    })
  }

  const response = await fetch(galaxyPath("/api/sentry/push/subscribe"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(subscriptionPayload(subscription)),
  })
  const payload = await readJsonResponse(response)
  if (!response.ok) return { ok: false, message: payload.error || "Galaxy could not save this browser." }
  return { ok: true, message: "Browser notifications enabled for this device." }
}

export async function sendSentryTestNotification() {
  const response = await fetch(galaxyPath("/api/sentry/test-notification"), { method: "POST" })
  const payload = await readJsonResponse(response)
  if (!response.ok) throw new Error(payload.error || "Galaxy could not send the test notification.")
  return payload
}

export function startSentryNotifications() {
  if (started) return
  started = true
  pollSentryEvent()
  window.setInterval(pollSentryEvent, POLL_INTERVAL_MS)
}
