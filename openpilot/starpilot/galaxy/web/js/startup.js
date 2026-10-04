export async function requestJson(url, { fetcher = (...args) => fetch(...args), timeout = 8000,
  later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id) } = {}) {
  const controller = new AbortController()
  let timer
  try {
    return await Promise.race([
      (async () => {
        const response = await fetcher(url, { cache: "no-store", credentials: "same-origin", signal: controller.signal })
        if (!response.ok) throw new Error("Galaxy could not be reached")
        return response.json()
      })(),
      new Promise((_, reject) => {
        timer = later(() => { controller.abort(); reject(new Error("Galaxy took too long to respond")) }, timeout)
      }),
    ])
  } finally {
    cancel(timer)
    controller.abort()
  }
}

export async function loadCatalog(options) {
  const [catalog, runtime] = await Promise.all([
    requestJson("./data/catalog.json", options), requestJson("./data/runtime.json", options),
  ])
  if (runtime?.schemaVersion !== 1 || !["sample", "local"].includes(runtime.monitor)) throw new Error("Invalid Galaxy runtime")
  const available = ["/system", "/navigation", "/manage_models", "/model_laboratory", "/cameras",
    "/developer/connect", "/device-preferences", "/driving", "/tuning", "/bluetooth", "/vehicle", "/theme_maker", "/galaxy", "/android-auto"]
  if (catalog?.mode !== "offline-preview" || !Array.isArray(catalog.tools) || catalog.tools.some(tool =>
    typeof tool?.path !== "string" || !tool.path.startsWith("/") || typeof tool.name !== "string" ||
    (tool.path === "/logs" ? tool.availability !== "partial-preview" :
      available.includes(tool.path) ? tool.availability !== "local-only" : tool.availability !== "unavailable"))) {
    throw new Error("Invalid Galaxy catalog")
  }
  return { tools: catalog.tools.slice().sort((a, b) => a.name.localeCompare(b.name)), mode: runtime.monitor }
}
