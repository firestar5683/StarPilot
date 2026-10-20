(() => {
  const original = window.fetch.bind(window)
  const pending = new Map()
  let sequence = 0
  window.__galaxyBleReply = (id, value) => {
    const item = pending.get(id)
    if (!item) return
    pending.delete(id)
    item.signal?.removeEventListener('abort', item.abort)
    if (value.error) { item.reject(new Error(value.error)); return }
    const data = Uint8Array.from(atob(value.body || ''), c => c.charCodeAt(0))
    item.resolve(new Response([204, 304].includes(value.status) ? null : data, {status: value.status, headers: value.headers}))
  }
  window.fetch = async (input, options = {}) => {
    const request = new Request(input, options)
    const url = new URL(request.url, location.href)
    if (url.origin !== location.origin) throw new Error('External resources are not available over Bluetooth. Connect using Galaxy Wi-Fi or LAN.')
    if (url.pathname === '/data/runtime.json') url.pathname = '/api/companion/runtime'
    if (!url.pathname.startsWith('/api/')) return original(input, options)
    if (['/api/companion/bluetooth', '/api/recordings/', '/api/replay/', '/api/cameras/', '/api/android-auto/upload', '/api/spotify/upload', '/api/navigation/map/tiles/'].some(path => url.pathname.startsWith(path)) ||
        ['/api/companion/uplink', '/api/companion/app.apk', '/api/auth/login', '/api/auth/logout'].includes(url.pathname)) {
      return new Response(JSON.stringify({error: 'This action is not available over Bluetooth. Connect using Galaxy Wi-Fi or LAN.', code: 'bluetooth_unavailable'}), {status: 501, headers: {'Content-Type': 'application/json'}})
    }
    if (request.signal.aborted) throw new DOMException('Request canceled', 'AbortError')
    const bytes = new Uint8Array(await request.arrayBuffer())
    if (bytes.length > 1048576) throw new Error('Large uploads are not available over Bluetooth. Connect using Galaxy Wi-Fi or LAN.')
    let body = ''
    for (let i = 0; i < bytes.length; i += 8192) body += String.fromCharCode(...bytes.subarray(i, i + 8192))
    const id = String(++sequence)
    return new Promise((resolve, reject) => {
      const abort = () => {
        pending.delete(id)
        StarPilotBLE.cancel(id)
        reject(new Error(['GET', 'HEAD'].includes(request.method) ? 'Bluetooth request canceled' : 'Connection interrupted. Check whether the change applied before retrying.'))
      }
      pending.set(id, {resolve, reject, signal: request.signal, abort})
      request.signal.addEventListener('abort', abort, {once: true})
      if (request.signal.aborted) { abort(); return }
      StarPilotBLE.request(id, JSON.stringify({method: request.method, path: url.pathname + url.search,
        headers: Object.fromEntries(request.headers), body: btoa(body)}))
    })
  }
})()
