export const MAX_RENDERED_ROUTES = 250
const SEARCH_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

function validDate(value) {
  if (!value) return null
  const date = value instanceof Date ? new Date(value.getTime()) : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function normalizeRouteSearchText(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLocaleLowerCase()
    .replace(/(\d+)(?:st|nd|rd|th)\b/g, "$1")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
}

export function formatRouteDate(value, locale) {
  const date = validDate(value)
  if (!date) return "Unknown date"
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "long",
    timeStyle: "short",
  }).format(date)
}

export function normalizeRoute(route, locale) {
  const timestamp = route?.timestamp == null ? null : String(route.timestamp)
  const startedAtDate = validDate(route?.startedAt)
  const timestampDate = validDate(timestamp)
  const routeDate = startedAtDate || timestampDate
  const displayDate = formatRouteDate(routeDate, locale)
  const isCustomName = Boolean(route?.isCustomName) || Boolean(timestamp && !timestampDate)
  const displayName = isCustomName ? timestamp : displayDate
  const dateAliases = routeDate ? [
    new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(routeDate),
    new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" }).format(routeDate),
    new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(routeDate),
    `${routeDate.getMonth() + 1}/${routeDate.getDate()}/${routeDate.getFullYear()}`,
    `${routeDate.getFullYear()}-${routeDate.getMonth() + 1}-${routeDate.getDate()}`,
  ] : []
  const timeAliases = routeDate ? [
    new Intl.DateTimeFormat(locale, { hour: "numeric", minute: "2-digit" }).format(routeDate),
    new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12: true }).format(routeDate),
    `${String(routeDate.getHours()).padStart(2, "0")}:${String(routeDate.getMinutes()).padStart(2, "0")}`,
  ] : []

  return {
    ...route,
    name: String(route?.name || ""),
    timestamp,
    startedAt: route?.startedAt || null,
    isCustomName,
    displayDate,
    displayName,
    _startedAtMs: startedAtDate?.getTime() ?? timestampDate?.getTime() ?? null,
    _searchIndex: {
      ids: [normalizeRouteSearchText(route?.name)].filter(Boolean),
      titles: [normalizeRouteSearchText(isCustomName ? displayName : "")].filter(Boolean),
      dates: dateAliases.map(normalizeRouteSearchText).filter(Boolean),
      times: timeAliases.map(normalizeRouteSearchText).filter(Boolean),
    },
  }
}

export function formatTotalDuration(seconds) {
  const totalMinutes = Math.max(0, Math.round(Number(seconds) / 60) || 0)
  if (totalMinutes < 1) return "0 min"
  if (totalMinutes < 60) return `${totalMinutes} min`
  const hours = Math.floor(totalMinutes / 60)
  const remaining = totalMinutes % 60
  return remaining > 0 ? `${hours}h ${remaining}m` : `${hours}h`
}

export function computeRouteStats(routes = []) {
  const list = Array.isArray(routes) ? routes : []
  let totalDurationSeconds = 0
  let preservedCount = 0
  let totalSegments = 0

  for (const route of list) {
    if (route) {
      if (Number.isFinite(route.approxDurationSeconds)) {
        totalDurationSeconds += Math.max(0, route.approxDurationSeconds)
      }
      if (route.is_preserved) {
        preservedCount += 1
      }
      if (Number.isFinite(route.segmentCount)) {
        totalSegments += Math.max(0, route.segmentCount)
      }
    }
  }

  return {
    count: list.length,
    totalDurationSeconds,
    formattedDuration: formatTotalDuration(totalDurationSeconds),
    preservedCount,
    totalSegments,
  }
}

export function sortRoutes(routes, sortOrder = "newest") {
  if (sortOrder === "longest" || sortOrder === "shortest") {
    const direction = sortOrder === "longest" ? -1 : 1
    return [...routes].sort((left, right) => {
      const leftDur = Number.isFinite(left?.approxDurationSeconds) ? left.approxDurationSeconds : -1
      const rightDur = Number.isFinite(right?.approxDurationSeconds) ? right.approxDurationSeconds : -1
      if (leftDur !== rightDur) return (leftDur - rightDur) * direction
      return String(left?.name || "").localeCompare(String(right?.name || ""))
    })
  }

  const direction = sortOrder === "oldest" ? 1 : -1
  return [...routes].sort((left, right) => {
    const leftTime = left?._startedAtMs
    const rightTime = right?._startedAtMs
    if (leftTime == null && rightTime == null) return String(left?.name || "").localeCompare(String(right?.name || ""))
    if (leftTime == null) return 1
    if (rightTime == null) return -1
    if (leftTime !== rightTime) return (leftTime - rightTime) * direction
    return String(left?.name || "").localeCompare(String(right?.name || "")) * -direction
  })
}

export function routeMatchesSearch(route, searchQuery) {
  const rawQuery = String(searchQuery || "").trim()
  const normalizedQuery = normalizeRouteSearchText(searchQuery)
  const queryTokens = normalizedQuery.split(" ").filter(Boolean)
  if (!queryTokens.length) return true

  const fallbackIndex = {
    ids: [route?.name],
    titles: [route?.timestamp, route?.displayName],
    dates: [route?.displayDate],
    times: [route?.displayDate],
  }
  const searchIndex = route?._searchIndex || Object.fromEntries(
    Object.entries(fallbackIndex).map(([key, values]) => [key, values.map(normalizeRouteSearchText).filter(Boolean)]),
  )

  const hasMonth = queryTokens.some(token => token.length >= 3 && SEARCH_MONTHS.some(month => month.startsWith(token)))
  const isDateQuery = hasMonth || /\d\s*[/-]\s*\d/.test(rawQuery) || /\d+(?:st|nd|rd|th)\b/i.test(rawQuery) || /^\d{4}$/.test(normalizedQuery)
  const isTimeQuery = /^\d{1,2}$/.test(normalizedQuery) || /\d\s*:\s*\d/.test(rawQuery) || queryTokens.some(token => token === "am" || token === "pm")
  const compactQuery = normalizedQuery.replaceAll(" ", "")
  const isHexQuery = /^[0-9a-f]+$/.test(compactQuery)
  const isIdQuery = rawQuery.includes("--") || (isHexQuery && (
    compactQuery.length >= 8 || (compactQuery.length >= 4 && /\d/.test(compactQuery) && /[a-f]/.test(compactQuery))
  ))
  const valuesFor = key => Array.isArray(searchIndex[key]) ? searchIndex[key] : []
  const matchesValue = (value, dateValue = false) => {
    if (value.includes(normalizedQuery)) return true
    const searchTokens = value.split(" ").filter(Boolean)
    return queryTokens.every(queryToken => searchTokens.some(searchToken => {
      // In a date query, "20" is a day prefix, not a match for the year "2026".
      if (dateValue && /^\d{1,2}$/.test(queryToken) && /^\d{4}$/.test(searchToken)) return false
      return searchToken.startsWith(queryToken)
    }))
  }

  return valuesFor("titles").some(value => matchesValue(value))
    || (isDateQuery && valuesFor("dates").some(value => matchesValue(value, true)))
    || (isTimeQuery && valuesFor("times").some(value => matchesValue(value)))
    || (isIdQuery && valuesFor("ids").some(value => matchesValue(value)))
}

export function buildRouteView(routes, options = {}) {
  const matching = sortRoutes(
    routes.filter(route => (!options.preservedOnly || route.is_preserved) && routeMatchesSearch(route, options.searchQuery)),
    options.sortOrder,
  )
  return {
    matching,
    visible: matching.slice(0, MAX_RENDERED_ROUTES),
    truncated: matching.length > MAX_RENDERED_ROUTES,
  }
}

export function routeViewRenderKey(routes, sortOrder = "newest", viewMode = "list") {
  const routeNames = Array.isArray(routes) ? routes.map(route => String(route?.name || "")).join(",") : ""
  return `${viewMode}:${sortOrder}:${routeNames}`
}

function localDayKey(date) {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

export function groupRoutesByDate(routes, now = new Date(), locale) {
  const today = validDate(now) || new Date()
  today.setHours(0, 0, 0, 0)
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const groups = []
  const byKey = new Map()

  for (const route of routes) {
    const routeDate = route?._startedAtMs == null ? null : new Date(route._startedAtMs)
    const key = routeDate ? localDayKey(routeDate) : "unknown"
    let group = byKey.get(key)
    if (!group) {
      let label = "Unknown date"
      if (routeDate) {
        if (key === localDayKey(today)) label = "Today"
        else if (key === localDayKey(yesterday)) label = "Yesterday"
        else label = new Intl.DateTimeFormat(locale, { dateStyle: "long" }).format(routeDate)
      }
      group = { key, label, routes: [] }
      byKey.set(key, group)
      groups.push(group)
    }
    group.routes.push(route)
  }
  return groups
}

export function groupRoutesForView(routes, sortOrder = "newest", now, locale) {
  // Date headers would scramble a duration sort, so show one flat group instead.
  if (sortOrder === "longest" || sortOrder === "shortest") {
    const list = Array.isArray(routes) ? [...routes] : []
    if (!list.length) return []
    return [{ key: sortOrder, label: sortOrder === "longest" ? "Longest first" : "Shortest first", routes: list }]
  }
  return groupRoutesByDate(routes, now, locale)
}

export function formatApproxDuration(seconds) {
  const minutes = Math.max(0, Math.round(Number(seconds) / 60) || 0)
  if (minutes < 1) return "Less than 1 min"
  if (minutes < 60) return `About ${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remaining = minutes % 60
  return `About ${hours} hr${remaining ? ` ${remaining} min` : ""}`
}

export function parseStoredSegmentNumber(segmentUrl) {
  const cleanPath = String(segmentUrl || "").split(/[?#]/, 1)[0]
  const match = cleanPath.match(/--(\d+)\/?$/)
  if (!match) return null
  const value = Number(match[1])
  return Number.isSafeInteger(value) ? value : null
}

export function getSegmentStatus(segmentUrls, playbackIndex) {
  if (!Array.isArray(segmentUrls) || !Number.isInteger(playbackIndex) || playbackIndex < 0 || playbackIndex >= segmentUrls.length) return ""
  const segmentNumber = parseStoredSegmentNumber(segmentUrls[playbackIndex])
  if (segmentNumber == null) return ""
  return `Segment ${segmentNumber}`
}

export function getSegmentOptions(segmentUrls) {
  if (!Array.isArray(segmentUrls)) return []
  return segmentUrls.map((_, index) => ({
    index,
    label: getSegmentStatus(segmentUrls, index) || `Clip ${index + 1}`,
  }))
}

export function cameraVideoUrl(segmentUrl, camera, quality) {
  const separator = String(segmentUrl).includes("?") ? "&" : "?"
  const url = `${segmentUrl}${separator}camera=${encodeURIComponent(camera)}`
  return quality ? `${url}&quality=${encodeURIComponent(quality)}` : url
}

export function routeMetadataErrorMessage(status, serverError) {
  if (status === 404) {
    return "This route is no longer available on this device. Its local video segments may have been deleted or moved."
  }
  const detail = String(serverError || "").trim()
  return detail || `Could not load route details (${status}).`
}

// loggerd only writes qcamera.ts alongside the road camera.
export function supportsLowQuality(camera) {
  return camera === "forward"
}

// qcamera is 526x330. Only a positively taller frame proves the real stream is already
// playing; an unknown height upgrades rather than stranding the viewer on the preview.
export function shouldUpgradeFromHeight(height) {
  return !(Number.isFinite(height) && height > 400)
}
