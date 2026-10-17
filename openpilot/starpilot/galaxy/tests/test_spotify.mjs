import assert from "node:assert/strict"
import { SpotifyFeed, SpotifyPage, archivePreflight, importProblem, installChecks, releaseInfo, serviceLabel,
  positionNow, formatTime, DOWNLOAD_PAGE } from "../web/js/spotify.js"

const setup = {
  enabled: true, parked: true, keyPresent: true, audioReady: true,
  release: { installed: true, version: "1.3.9.32", expires: "2027-01-14T00:00:00+00:00", daysLeft: 80, level: "ok", expired: false },
  preferences: { deviceName: "StarPilot", cacheMb: 256, initialVolume: 60, output: "bluetooth", outputAddress: "AA:BB:CC:DD:EE:FF", outputName: "Car" },
  devices: [{ address: "AA:BB:CC:DD:EE:FF", name: "Car", connected: true }], service: null,
  import: { state: "idle" }, maxUploadBytes: 64 * 1024 * 1024, archiveName: "soloist_release_arm64.tar.gz", cacheChoices: [100, 256],
  links: { download: DOWNLOAD_PAGE, key: "https://developer.spotify.com/dashboard/soloist", help: "https://developer.spotify.com/" },
}

assert.equal(archivePreflight({ name: "soloist_release_arm64.tar.gz" }), "")
assert.equal(archivePreflight({ name: "soloist_release_arm64.tgz" }), "")
assert.match(archivePreflight({ name: "soloist_release_x86_64.tar.gz" }), /different computer/)
assert.match(archivePreflight({ name: "soloist_release_arm64.tar" }), /unpacked the download/)
assert.match(archivePreflight({ name: "soloist" }), /unpacked player/)
assert.match(archivePreflight({ name: "photo.jpg" }), /Choose the soloist_release_arm64/)

assert.match(importProblem({ state: "failed", code: "NOT_OFFICIAL" }), /doesn’t match/)
assert.match(importProblem({ state: "failed", code: "OFFLINE" }), /internet/)
assert.equal(importProblem({ state: "done" }), "")
assert.deepEqual(installChecks({ state: "running", stage: "verifying" }).map((c) => c.status), ["done", "done", "active", "pending", "pending"])
assert.deepEqual(installChecks({ state: "failed", stage: "verifying", code: "NOT_OFFICIAL" }).map((c) => c.status),
  ["done", "done", "failed", "pending", "pending"])
assert.ok(installChecks({ state: "done" }).every((c) => c.status === "done"))

assert.equal(releaseInfo({ installed: false }).level, "none")
assert.equal(releaseInfo({ ...setup.release, level: "soon", daysLeft: 1 }, "en-US").label, "Version 1.3.9.32 · expires in 1 day")
assert.equal(releaseInfo({ ...setup.release, expired: true }, "en-US").level, "expired")

assert.equal(serviceLabel({ enabled: false }), "Off")
assert.equal(serviceLabel({ enabled: true, service: { state: "waiting_output", message: "Waiting for Car to connect over Bluetooth." } }),
  "Waiting for Car to connect over Bluetooth.")
assert.match(serviceLabel({ enabled: true, service: { state: "waiting", message: "" } }), /pick this device/)
assert.equal(serviceLabel({ enabled: true, service: { state: "ready", player: { status: "paused" } } }), "Paused")

assert.equal(positionNow({ ms: 1000, at: 10_000, speed: 1 }, 5000, 12_000), 3000)
assert.equal(positionNow({ ms: 1000, at: 10_000, speed: 0 }, 5000, 99_000), 1000)
assert.equal(positionNow({ ms: 4000, at: 10_000, speed: 1 }, 5000, 99_000), 5000)
assert.equal(formatTime(65_000), "1:05")

// The key is only ever sent; status responses never carry it, and the page has no field that shows it.
assert.match(SpotifyPage.template, /type="password" v-model="keyValue"/)
assert.match(SpotifyPage.template, /rel="noopener noreferrer"/)
assert.doesNotMatch(SpotifyPage.template, /setup\.key\b/)

const published = []
const requests = []
const feed = new SpotifyFeed({
  publish: (value) => published.push(value),
  later: () => 1, cancelTimer: () => { },
  fetcher: async (path, options) => {
    requests.push([path, options?.method || "GET", options?.body])
    return { ok: true, status: 200, json: async () => setup }
  },
})
await feed.start()
assert.deepEqual(feed.setup, setup)
await feed.post("./api/spotify/key", { key: "sk_live_0123456789abcdef" })
assert.equal(requests.at(-2)[0], "./api/spotify/key")
assert.equal(feed.error, "")
await feed.control("volume", { volume: 40 })
assert.deepEqual(JSON.parse(requests.at(-1)[2]), { action: "volume", args: { volume: 40 } })
feed.stop()
console.log("spotify ok")
