// Android owns pairing and BLE; Galaxy sees ordinary fetch Responses.
(() => {
  const origin = 'https://appassets.androidplatform.net'
  if (location.origin !== origin || window !== window.top || !window.GalaxyNative) return
  const pending = new Map()
  const originalFetch = window.fetch.bind(window)
  const abortError = () => new DOMException('Request cancelled', 'AbortError')
  const encode = bytes => {
    let text = ''
    for (let start = 0; start < bytes.length; start += 8192) text += String.fromCharCode(...bytes.subarray(start, start + 8192))
    return btoa(text)
  }
  GalaxyNative.onmessage = ({ data }) => {
    let reply
    try { reply = JSON.parse(data) } catch { return }
    const task = pending.get(reply.id)
    if (!task) return
    pending.delete(reply.id)
    task.cleanup()
    if (!reply.ok) { task.reject(new Error(reply.error || 'Bluetooth request failed')); return }
    try {
      const response = reply.response
      const raw = atob(response.body)
      if (raw.length > 1048576) throw new Error('Response exceeds the 1 MiB Bluetooth limit')
      const bytes = Uint8Array.from(raw, ch => ch.charCodeAt(0))
      task.resolve(new Response([204, 205, 304].includes(response.status) || task.head ? null : bytes,
        { status: response.status, headers: response.headers }))
    } catch (error) { task.reject(error) }
  }
  window.fetch = async (input, init) => {
    const request = new Request(input instanceof Request ? input : new URL(input, location.href), init)
    const url = new URL(request.url)
    const dynamic = url.origin === origin && (url.pathname.startsWith('/api/') || url.pathname === '/assets/components/tools/device_settings_layout.json')
    if (!dynamic) return originalFetch(request)
    if (request.signal.aborted) throw abortError()
    const bytes = new Uint8Array(await request.arrayBuffer())
    if (bytes.length > 1048576) throw new Error('Upload exceeds the 1 MiB Bluetooth limit')
    if (request.signal.aborted) throw abortError()
    const id = crypto.randomUUID()
    const headers = Object.fromEntries(request.headers.entries())
    return new Promise((resolve, reject) => {
      let timeout
      const cleanup = () => { clearTimeout(timeout); request.signal.removeEventListener('abort', cancel) }
      const cancel = () => {
        if (!pending.delete(id)) return
        cleanup()
        GalaxyNative.postMessage(JSON.stringify({ id, cancel: true }))
        reject(abortError())
      }
      pending.set(id, { resolve, reject, cleanup, head: request.method === 'HEAD' })
      request.signal.addEventListener('abort', cancel, { once: true })
      timeout = setTimeout(() => {
        if (!pending.delete(id)) return
        cleanup()
        GalaxyNative.postMessage(JSON.stringify({ id, cancel: true }))
        reject(new Error('Bluetooth request timed out. Reconnect and check its result before retrying.'))
      }, 110000)
      try { GalaxyNative.postMessage(JSON.stringify({ id, path: url.pathname + url.search, method: request.method, headers, body: encode(bytes) })) }
      catch (error) { pending.delete(id); cleanup(); reject(error) }
    })
  }
})()
