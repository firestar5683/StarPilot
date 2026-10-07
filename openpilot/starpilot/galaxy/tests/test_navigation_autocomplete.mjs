import assert from "node:assert/strict"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { NavigationClient, NavigationPage, validDestination } from "../web/js/navigation.js"

const home = { id: "h1", name: "12 Elm St", latitude: 40.1, longitude: -90.1 }
const gym = { id: "g1", name: "Elm Fitness", latitude: 40.3, longitude: -90.3 }
const status = { enabled: true, isMetric: false, hasKey: true, status: "noDestination", revision: "r1", destination: null,
  favorites: [home, gym], route: [], instruction: null, location: null }
const suggestion = (id, searchId) => ({ id, name: "Coffee " + id, description: "Main St", searchId, temporary: true })

assert.equal(validDestination(home), true)

// Suggestions share one search session while typing and never cancel status polling.
const requests = []
const client = new NavigationClient({ publish() {}, later: () => 1, cancelTimer() {},
  fetcher: async (url, options = {}) => {
    const body = options.body ? JSON.parse(options.body) : null
    requests.push({ url, body, signal: options.signal })
    const payload = url.endsWith("/status") ? status : { results: [suggestion("a", body.searchId), suggestion("b", body.searchId)] }
    return { ok: true, status: 200, json: async () => payload }
  } })
await client.start()
assert.equal(client.data.revision, "r1")
const first = await client.suggest("cof")
const second = await client.suggest("coffee")
const typed = requests.filter((request) => request.body?.autocomplete === true)
assert.equal(typed.length, 2)
assert.equal(typed[0].body.searchId, typed[1].body.searchId, "one session for the whole typing burst")
assert.equal(typed[0].body.clientId, client.clientId)
assert.equal(first.length, 2)
assert.deepEqual(second.map((place) => place.name), ["Coffee a", "Coffee b"])
assert.deepEqual(await client.suggest("co"), [], "two letters are too few to suggest")
assert.equal(client.suggestions.length, 0)

// A status poll while typing does not abort the suggestion request (and vice versa).
const slow = []
const parallel = new NavigationClient({ publish() {}, later: () => 1, cancelTimer() {},
  fetcher: (url, options = {}) => new Promise((resolve) => slow.push({ url, options, resolve })) })
parallel.active = true
parallel.data = status
const pendingSuggest = parallel.suggest("coffee")
const pendingStatus = parallel.run("status")
assert.equal(slow.length, 2)
assert.equal(slow[0].options.signal.aborted, false, "status polling leaves the suggestion request alone")
slow[0].resolve({ ok: true, status: 200, json: async () => ({ results: [suggestion("c", JSON.parse(slow[0].options.body).searchId)] }) })
slow[1].resolve({ ok: true, status: 200, json: async () => status })
assert.equal((await pendingSuggest).length, 1)
await pendingStatus
parallel.stop()

// Choosing a suggestion or running a full search ends the typing session.
const chosen = client.suggestions[0] || second[0]
await client.choose(chosen)
const select = requests.at(-1)
assert.deepEqual(select.body, { action: "selectPlace", revision: "r1", id: "a", searchId: typed[0].body.searchId })
await client.suggest("tea")
const afterChoice = requests.filter((request) => request.body?.autocomplete === true).at(-1)
assert.notEqual(afterChoice.body.searchId, typed[0].body.searchId, "a new typing burst gets a new session")
await client.search("12 Elm St")
assert.equal(requests.at(-1).body.autocomplete, undefined, "the Search button is a full search")
assert.ok(requests.at(-1).body.searchId, "with its own search session, as upstream does")
assert.equal(client.suggestions.length, 0)
client.stop()

// A refused session (expired or settings changed) is replaced on the next keystroke.
let refuse = true
const refused = new NavigationClient({ publish() {}, later: () => 1, cancelTimer() {},
  fetcher: async (_url, options) => ({ ok: !refuse, status: refuse ? 400 : 200,
    json: async () => refuse ? { error: "Start a new destination search" } : { results: [suggestion("d", JSON.parse(options.body).searchId)] } }) })
refused.active = true
refused.data = status
assert.deepEqual(await refused.suggest("coffee"), [])
const stale = refused.autocompleteId
assert.equal(stale, null)
refuse = false
assert.equal((await refused.suggest("coffee")).length, 1)

// Page logic: matching saved places show first in the dropdown.
const computed = NavigationPage.computed
const page = { data: status, query: "elm", suggestOpen: true, suggestions: [] }
page.favoriteMatches = computed.favoriteMatches.call(page)
assert.deepEqual(page.favoriteMatches.map((place) => place.id), ["h1", "g1"])
assert.equal(computed.showSuggestions.call(page), true)
assert.equal(computed.showSuggestions.call({ ...page, favoriteMatches: [], suggestions: [] }), false)
const usage = { searchSessions: { used: 12, limit: 495, free: 500 }, directions: { used: 3, limit: 99000, free: 100000 }, staticTiles: { used: 0, limit: 198000, free: 200000 } }
assert.deepEqual(computed.usageRows.call({ data: { mapboxUsage: usage } }).map((row) => [row.label, row.used, row.limit]),
  [["Searches", 12, 495], ["Routes", 3, 99000], ["Map views", 0, 198000]])

compile(NavigationPage.template, { decodeEntities: (value) => value.replaceAll("&amp;", "&") })
console.log("Navigation autocomplete: one session per typing burst, parallel polling, session reset, usage and template passed")
