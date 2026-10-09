import assert from "node:assert/strict"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { FavoriteChoices, NavigationClient, NavigationPage, validDestination } from "../web/js/navigation.js"

const home = { id: "h1", name: "12 Elm St", latitude: 40.1, longitude: -90.1 }
const gym = { id: "g1", name: "Elm Fitness", latitude: 40.3, longitude: -90.3 }
const status = { enabled: true, isMetric: false, hasKey: true, status: "noDestination", revision: "r1", destination: null,
  favorites: [home, gym], route: [], instruction: null, location: null }
const suggestion = (id, searchId) => ({ id, name: "Coffee " + id, description: "Main St", searchId })

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
const searchRequests = requests.length
assert.deepEqual((await client.search("coffee")).results, second)
assert.equal(requests.length, searchRequests, "Search reuses matching suggestions without another provider request")
assert.equal(client.searchId, typed[0].body.searchId, "reused places keep their retrieval session")
await client.suggest("coffee")
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

// Page logic: saved and recent places match first in the dropdown; an empty box lists them all.
const computed = NavigationPage.computed
const recent = { id: "r1", name: "Elm Diner", address: "5 Oak Ave", latitude: 40.5, longitude: -90.5 }
const evaluate = (state) => {
  const page = { suggestOpen: true, suggestions: [], results: [], ...state }
  for (const name of ["ready", "favorites", "savedIds", "recents", "shortcuts", "localMatches", "showQuick", "showSuggestions", "showShortcuts"])
    page[name] = computed[name].call(page)
  return page
}
let page = evaluate({ data: { ...status, recents: [recent, home] }, query: "elm" })
assert.deepEqual(page.recents.map((place) => place.id), ["r1"], "recents leave out places that are already saved")
assert.deepEqual(page.localMatches.map((place) => place.id), ["h1", "g1", "r1"])
assert.equal(page.showSuggestions, true)
assert.deepEqual(evaluate({ data: status, query: "oak" }).localMatches, [], "only this page's places are matched")
assert.deepEqual(evaluate({ data: { ...status, recents: [recent] }, query: "oak" }).localMatches.map((place) => place.id), ["r1"], "addresses match too")
assert.equal(evaluate({ data: status, query: "zzz" }).showSuggestions, false)
page = evaluate({ data: { ...status, recents: [recent] }, query: "" })
assert.equal(page.showQuick, true)
assert.equal(page.showShortcuts, false, "one-tap places hide while the list is open")
page = evaluate({ data: { ...status, recents: [recent] }, query: "", suggestOpen: false })
assert.deepEqual([page.showQuick, page.showShortcuts], [false, true])
assert.equal(evaluate({ data: { ...status, destination: home }, query: "", suggestOpen: false }).showShortcuts, false)
const methods = NavigationPage.methods
const labeled = { ...home, label: "home" }
assert.deepEqual([methods.placeName(labeled), methods.placeDetail(labeled)], ["Home", "12 Elm St"])
assert.equal(methods.placeIcon.call({ isFavorite: () => true }, labeled), "bi-house-fill")
const actions = []
await methods.setLabel.call({ client: { action: async (...args) => actions.push(args) } }, labeled, "home")
assert.deepEqual(actions.at(-1), ["labelFavorite", { id: "h1", label: null }], "choosing the current label clears it")
const usage = { searchSessions: { used: 12, limit: 495, free: 500 }, geocoding: { used: 4, limit: 99000, free: 100000 },
  directions: { used: 3, limit: 99000, free: 100000 }, staticTiles: { used: 0, limit: 198000, free: 200000 } }
assert.deepEqual(computed.usageRows.call({ data: { mapboxUsage: usage } }).map((row) => [row.label, row.used, row.limit]),
  [["Searches", 12, 495], ["Address lookups", 4, 99000], ["Routes", 3, 99000], ["Map views", 0, 198000]])

compile(NavigationPage.template, { decodeEntities: (value) => value.replaceAll("&amp;", "&") })
compile(FavoriteChoices.template, { decodeEntities: value => value.replaceAll("&amp;", "&") })
const favoriteActions = [], favoritePage = { favorites: [], savedSearchIds: [], savedSuggestionPlaces: {}, favoritePicker: "selected",
  client: { save: async (place, label) => { favoriteActions.push([place, label]); return {favorites:[{...home,label}]} } } }
await methods.saveAs.call(favoritePage, home, "home")
assert.deepEqual(favoriteActions[0], [home, "home"])
assert.equal(favoritePage.favoritePicker, null)
favoritePage.favorites = [{...home,label:"home"}]
favoritePage.client.action = async (...args) => { favoriteActions.push(args); return {favorites:[home]} }
await methods.saveAs.call(favoritePage, home, null)
assert.deepEqual(favoriteActions.at(-1), ["labelFavorite", {id:home.id,label:null}], "Other clears Home/Work without removing the favorite")
favoritePage.favoritePicker = "selected"
favoritePage.client.action = async () => null
await methods.saveAs.call(favoritePage, home, "work")
assert.equal(favoritePage.favoritePicker, "selected", "failed saves leave the inline choices open")
console.log("Navigation autocomplete: one session per typing burst, parallel polling, session reset, usage and template passed")


// Stars select categories; the separate remove action clears persisted IDs and suggestion markers.
{
  const suggestion = { id: 'search-result', searchId: 'search-session', name: 'Cafe' }
  const saved = { id: 'saved-cafe', name: 'Cafe', latitude: 36, longitude: -115 }
  const page = { favorites: [saved], savedSearchIds: [suggestion.id],
    savedSuggestionPlaces: { [suggestion.id]: saved.id }, favoritePicker: 'old-picker' }
  Object.defineProperty(page, 'savedIds', { get: () => new Set(page.favorites.map(place => place.id)) })
  for (const name of ['isFavorite', 'favoriteKey', 'openFavorite', 'removeFavorite', 'saveAs']) page[name] = methods[name].bind(page)
  const removed = [], savedPlaces = []
  page.client = {
    action: async (action, value) => { removed.push([action, value]); page.favorites = []; return { favorites: [] } },
    save: async (place, label) => { savedPlaces.push([place, label]); return { favorites: [] } },
  }
  assert.equal(page.isFavorite(suggestion), true)
  page.openFavorite(suggestion)
  assert.equal(page.favoritePicker, page.favoriteKey(suggestion))
  assert.deepEqual(removed, [], 'the star opens categories without removing a favorite')
  await page.removeFavorite(suggestion)
  assert.deepEqual(removed, [['removeFavorite', { id: saved.id }]])
  assert.equal(page.isFavorite(suggestion), false)
  assert.deepEqual(page.savedSearchIds, [])
  assert.deepEqual(page.savedSuggestionPlaces, {})
  assert.equal(page.favoritePicker, null)
  const other = { ...saved, id: 'another-place', name: 'Park' }
  page.openFavorite(other)
  assert.equal(page.favoritePicker, page.favoriteKey(other))
  await page.saveAs(other, null)
  assert.deepEqual(savedPlaces, [[other, null]], 'another Other favorite can be saved after removing one')

  page.savedSuggestionPlaces[suggestion.id] = saved.id
  page.savedSearchIds = [suggestion.id]
  assert.equal(page.isFavorite(suggestion), false, 'a stale suggestion marker cannot override a refreshed saved list')
  page.favorites = [saved]
  page.client.action = async () => null
  await page.removeFavorite(suggestion)
  assert.equal(page.isFavorite(suggestion), true, 'failed removal preserves the saved place for retry')
  assert.equal(page.savedSuggestionPlaces[suggestion.id], saved.id)
  await page.openFavorite(saved)
  assert.equal(page.favoritePicker, page.favoriteKey(saved), 'the filled star opens the category picker')
}
assert.match(NavigationPage.template, /@click="removeFavorite\(place\)"><i class="bi bi-x-lg"/)
assert.doesNotMatch(NavigationPage.template, /bi-three-dots/)
console.log('Favorites: category picker, separate removal, another save, refreshed state and failed-removal retry passed')
