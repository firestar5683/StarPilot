export async function requestJson(url, { fetcher = (...args) => fetch(...args), timeout = 8000,
  later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id), request = {}, withResponse = false } = {}) {
  const controller = new AbortController()
  let timer
  let rejectCanceled
  const abort = () => { controller.abort(); rejectCanceled?.(Object.assign(new Error("Request canceled"), { name: "AbortError" })) }
  request.signal?.addEventListener("abort", abort, { once: true })
  try {
    return await Promise.race([
      new Promise((_, reject) => { rejectCanceled = reject; if (request.signal?.aborted) abort() }),
      (async () => {
        const response = await fetcher(url, { ...request, cache: "no-store", credentials: "same-origin", signal: controller.signal })
        if (!response.ok && !withResponse) {
          const body = await response.json?.().catch(() => null)
          const error = new Error(typeof body?.error === "string" ? body.error : "Galaxy could not be reached")
          error.status = response.status
          error.code = body?.code
          throw error
        }
        const data = await response.json()
        return withResponse ? { response, data } : data
      })(),
      new Promise((_, reject) => {
        timer = later(() => { controller.abort(); reject(Object.assign(new Error("Galaxy took too long to respond"), { name: "TimeoutError" })) }, timeout)
      }),
    ])
  } finally {
    request.signal?.removeEventListener("abort", abort)
    cancel(timer)
    controller.abort()
  }
}

export async function loadCatalog(options) {
  const [catalog, runtime] = await Promise.all([
    requestJson("./data/catalog.json", options), requestJson("./data/runtime.json", options),
  ])
  if (runtime?.schemaVersion !== 1 || !["sample", "local"].includes(runtime.monitor)) throw new Error("Invalid Galaxy runtime")
  if (catalog?.mode !== "offline-preview" || !Array.isArray(catalog.tools) || catalog.tools.some(tool =>
    typeof tool?.path !== "string" || !tool.path.startsWith("/") || typeof tool.name !== "string" ||
    !["partial-preview", "local-only", "unavailable"].includes(tool.availability) ||
    typeof tool.icon !== "string" || typeof tool.description !== "string" ||
    (tool.visibility !== undefined && tool.visibility !== "authenticated"))) {
    throw new Error("Invalid Galaxy catalog")
  }
  return { tools: catalog.tools.slice().sort((a, b) => a.name.localeCompare(b.name)), mode: runtime.monitor }
}
