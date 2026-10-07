import { GxNotice } from "./notice.js"
import { markRaw } from "../vendor/vue/vue.esm-browser.js"

const SIZE = 512
const locationDeadlines = new WeakMap()
export function project(point, zoom) {
  const latitude = Math.max(-85.05112878, Math.min(85.05112878, point.latitude))
  const sine = Math.sin(latitude * Math.PI / 180), world = SIZE * 2 ** zoom
  return [(point.longitude + 180) / 360 * world, (0.5 - Math.log((1 + sine) / (1 - sine)) / (4 * Math.PI)) * world]
}
export function unproject(x, y, zoom) {
  const world = SIZE * 2 ** zoom
  return {
    longitude: ((x / world * 360) % 360 + 360) % 360 - 180, latitude: Math.atan(Math.sinh(Math.PI * (1 - 2 * y / world))) * 180 / Math.PI
  }
}
// Screen pixels per meter at a latitude: the circles for offline areas are true ground distances.
export function metersPerPixelInverse(latitude, zoom) {
  return SIZE * 2 ** zoom / (40075016.686 * Math.max(0.01, Math.cos(latitude * Math.PI / 180)))
}
export function relativeX(x, center, world) {
  return center + ((x - center + world / 2) % world + world) % world - world / 2
}
export class RasterMap {
  constructor(canvas, changed = () => {}) {
    this.canvas = canvas;
    this.changed = changed;
    this.zoom = 2;
    this.center = {
      longitude: 0, latitude: 0
    };
    this.failed = new Set();
    this.tiles = new Map();
    this.pending = new Map();
    this.closed = false;
    this.data = {};
    this.initialized = false
    // Circles drawn over the map ({ latitude, longitude, radiusKm, stroke, fill }) and a tap callback (latitude, longitude).
    this.overlays = [];
    this.onTap = null
    this.observer = new ResizeObserver(() => this.draw());
    this.observer.observe(canvas)
    this.down = (event) => {
      this.press = [event.clientX, event.clientY]
      this.userPanned = true
      this.drag = [event.clientX, event.clientY, ...project(this.center, this.zoom)];
      canvas.setPointerCapture(event.pointerId)
    }
    this.move = (event) => {
      if (!this.drag) return;
      this.center = unproject(this.drag[2] - event.clientX + this.drag[0], this.drag[3] - event.clientY + this.drag[1], this.zoom);
      this.requestDraw()
    }
    this.up = (event) => {
      this.drag = null
      const press = this.press
      this.press = null
      if (press && event?.type === 'pointerup' && this.onTap && Math.hypot(event.clientX - press[0], event.clientY - press[1]) < 6) {
        const rect = this.canvas.getBoundingClientRect(), [cx, cy] = project(this.center, this.zoom)
        this.onTap(unproject(cx - rect.width / 2 + event.clientX - rect.left, cy - rect.height / 2 + event.clientY - rect.top, this.zoom))
      }
    }
    this.key = (event) => {
      const delta = {
        ArrowLeft: [-80, 0], ArrowRight: [80, 0], ArrowUp: [0, -80], ArrowDown: [0, 80]
      }
      [event.key];
      if (delta) {
        event.preventDefault();
        this.userPanned = true
        const [x,y] = project(this.center,this.zoom);
        this.center = unproject(x+delta[0],y+delta[1],this.zoom);
        this.draw()
      }
    }
    this.wheel = (event) => {
      event.preventDefault();
      // Trackpads send dozens of small wheel events per gesture; one zoom level per 100px, at most every 120 ms.
      this.wheelDelta = (this.wheelDelta || 0) + (event.deltaMode === 1 ? event.deltaY * 33 : event.deltaY)
      const now = performance.now()
      if (Math.abs(this.wheelDelta) < 100 || now - (this.lastWheelZoom || 0) < 120) return
      this.changeZoom(this.wheelDelta < 0 ? 1 : -1)
      this.wheelDelta = 0
      this.lastWheelZoom = now
    }
    for (const [name, listener] of [['pointerdown', this.down], ['pointermove', this.move], ['pointerup', this.up], ['pointercancel', this.up], ['wheel', this.wheel], ['keydown', this.key]]) canvas.addEventListener(name, listener, {
      passive: false
    })
  }
  update(data, stale) {
    clearTimeout(this.locationTimer)
    const now = performance.now()
    if (data && !locationDeadlines.has(data)) {
      locationDeadlines.set(data, data.location?.expiresAt ?? now + (data.location?.validForMs ?? 0))
    }
    const remaining = Math.max(0, (data && locationDeadlines.get(data) || 0) - now)
    this.locationFresh = !stale && remaining > 0
    if (this.locationFresh) {
      this.locationTimer = setTimeout(() => {
        this.locationFresh = false;
        this.changed();
        this.draw()
      }, remaining)
    }
    const firstLiveFix = this.locationFresh && this.lastLocation?.lastKnown === true
    if (data?.location && (this.locationFresh || data.location.lastKnown === true && !this.lastLocation)) {
      this.lastLocation = { ...data.location, bearing: Number.isFinite(data.location.bearing) ? data.location.bearing : this.lastLocation?.bearing }
    }
    this.data = data || {}
    this.stale = stale
    if (firstLiveFix && !this.userPanned) this.recenter()
    if (!this.initialized && (data?.location || data?.destination)) {
      this.recenter()
      this.initialized = true
    }
    this.changed()
    this.draw()
  }
  recenter() {
    const point = this.lastLocation || this.data.destination;
    if (point) {
      this.center = point;
      this.zoom = this.lastLocation ? 15 : 2
    }
    this.draw()
  }
  requestDraw() {
    this.frameScheduled ??= requestAnimationFrame(() => { this.frameScheduled = null; this.draw() })
  }
  // The nearest loaded ancestor of a missing tile, and the part of it that covers the tile.
  placeholder(zoom, x, y) {
    for (let up = 1; up <= 5 && zoom - up >= 0; up++) {
      const image = this.tiles.get(`${zoom - up}/${x >> up}/${y >> up}`)
      if (image) {
        const span = SIZE / 2 ** up
        return [image, (x - ((x >> up) << up)) * span, (y - ((y >> up) << up)) * span, span]
      }
    }
    return null
  }
  changeZoom(delta) {
    this.zoom = Math.max(0, Math.min(18, this.zoom + delta));
    this.draw()
  }
  draw() {
    if (this.closed) return
    const width = Math.max(1, Math.round(this.canvas.clientWidth)), height = Math.max(1, Math.round(this.canvas.clientHeight));
    if (this.canvas.width !== width) this.canvas.width = width;
    if (this.canvas.height !== height) this.canvas.height = height
    const ctx = this.canvas.getContext('2d'), [cx, cy] = project(this.center, this.zoom), n = 2 ** this.zoom, world = SIZE * n, needed = new Set()
    ctx.fillStyle = '#0e0e1a';
    ctx.fillRect(0, 0, width, height)
    for (let ty = Math.floor((cy - height / 2) / SIZE); ty <= Math.floor((cy + height / 2) / SIZE); ty++) {
      if (ty < 0 || ty >= n) continue
      for (let tx = Math.floor((cx - width / 2) / SIZE); tx <= Math.floor((cx + width / 2) / SIZE); tx++) {
        const x = ((tx % n) + n) % n, key = `${this.zoom}/${x}/${ty}`;
        needed.add(key)
        const image = this.tiles.get(key), left = tx * SIZE - cx + width / 2, top = ty * SIZE - cy + height / 2
        if (image) ctx.drawImage(image, left, top, SIZE, SIZE)
        else {
          // A stretched coarser tile while this one loads, so zooming in never shows blank squares.
          const cover = this.placeholder(this.zoom, x, ty)
          if (cover) ctx.drawImage(cover[0], cover[1], cover[2], cover[3], cover[3], left, top, SIZE, SIZE)
        }
      }
    }
    for (const [key, controller] of this.pending) if (!needed.has(key)) {
      controller.abort();
      this.pending.delete(key)
    }
    for (const key of needed) if (!this.tiles.has(key) && !this.pending.has(key) && !this.failed.has(key) && this.pending.size < 6) this.load(key)
    const pixel = (point) => {
      const [x, y] = project(point, this.zoom);
      return [relativeX(x, cx, world) - cx + width / 2, y - cy + height / 2]
    }
    for (const circle of this.overlays) {
      const [x, y] = pixel(circle), radius = metersPerPixelInverse(circle.latitude, this.zoom) * circle.radiusKm * 1000
      ctx.beginPath(); ctx.arc(x, y, Math.max(2, radius), 0, Math.PI * 2)
      ctx.fillStyle = circle.fill; ctx.fill()
      ctx.setLineDash(circle.dash || []); ctx.strokeStyle = circle.stroke; ctx.lineWidth = circle.width || 2; ctx.stroke(); ctx.setLineDash([])
    }
    for (const choice of this.data.alternatives || []) {
      if (choice.index === this.data.selectedRoute || !choice.geometry?.length) continue
      ctx.beginPath(); choice.geometry.forEach((point,index) => { const xy=pixel(point); index ? ctx.lineTo(...xy) : ctx.moveTo(...xy) });
      ctx.strokeStyle='#7885a6'; ctx.lineWidth=4; ctx.stroke()
    }
    if (this.data.route?.length) {
      ctx.beginPath();
      this.data.route.forEach((point, index) => {
        const xy = pixel(point);
        index ? ctx.lineTo(...xy) : ctx.moveTo(...xy)
      });
      ctx.strokeStyle = '#b68cff';
      ctx.lineWidth = 5;
      ctx.stroke()
    }
    for (const [point, color] of [[this.data.destination, '#ffbd59'], [this.lastLocation, this.locationFresh ? '#65c8ff' : '#9aa6bb']]) if (point) {
      const xy = pixel(point);
      ctx.beginPath();
      ctx.arc(...xy, 7, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke()
      if (point === this.lastLocation && Number.isFinite(point.bearing)) {
        ctx.save(); ctx.translate(...xy); ctx.rotate(point.bearing * Math.PI / 180);
        ctx.beginPath(); ctx.moveTo(0,-22); ctx.lineTo(-7,-11); ctx.lineTo(7,-11); ctx.closePath();
        ctx.fillStyle = color; ctx.fill(); ctx.restore()
      }
    }
  }
  async load(key) {
    const controller = new AbortController();
    this.pending.set(key, controller);
    let timedOut = false
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort()
    }, 8000)
    try {
      const response = await fetch(`./api/navigation/map/tiles/${key}.png`, {
        credentials: 'same-origin', signal: controller.signal
      });
      if (!response.ok) throw new Error('Map tiles unavailable')
      const image = await createImageBitmap(await response.blob());
      if (this.closed || controller.signal.aborted) {
        image.close();
        return
      }
      this.tiles.set(key, image);
      this.failures = 0
      while (this.tiles.size > 160) {
        const oldest = this.tiles.keys().next().value;
        this.tiles.get(oldest).close();
        this.tiles.delete(oldest)
      }
      if (!this.failed.size) this.changed('')
    } catch (error) {
      if (timedOut || !controller.signal.aborted) {
        this.failed.add(key);
        if (this.failed.size > 64) this.failed.delete(this.failed.values().next().value);
        // A quick refusal (a busy moment) is retried quickly and silently; a hung request or a run of failures is reported.
        this.failures = (this.failures || 0) + 1
        const persistent = timedOut || this.failures >= 6
        if (persistent) this.changed('Map tiles unavailable. Check the saved key and connection. Reconnecting automatically…')
        this.retryTimer ??= setTimeout(() => { this.retryTimer = null; this.retry() }, persistent ? 5000 : 800)
      }
    } finally {
      clearTimeout(timer);
      if (this.pending.get(key) === controller) this.pending.delete(key);
      if (!this.closed) {
        /* Paint completed tiles without continuously retrying failures. */ this.paintScheduled ??= requestAnimationFrame(() => {
          this.paintScheduled = null;
          this.draw()
        })
      }
    }
  }
  retry() {
    this.failed.clear();
    this.draw()
  }
  close() {
    this.closed = true;
    clearTimeout(this.locationTimer);
    clearTimeout(this.retryTimer);
    this.observer.disconnect();
    cancelAnimationFrame(this.paintScheduled);
    if (this.frameScheduled) cancelAnimationFrame(this.frameScheduled);
    for (const controller of this.pending.values()) controller.abort();
    for (const image of this.tiles.values()) image.close();
    this.tiles.clear();
    for (const [name, listener] of [['pointerdown', this.down], ['pointermove', this.move], ['pointerup', this.up], ['pointercancel', this.up], ['wheel', this.wheel], ['keydown', this.key]]) this.canvas.removeEventListener(name, listener)
  }
}
export const NavigationMap = {
  components: { GxNotice },
  props: ['data', 'stale'], data: () => ({
    error: '', map: null, locationFresh: false, lastLocation: null
  }),
  mounted() {
    this.map = markRaw(new RasterMap(this.$refs.canvas, (error) => {
      if (error !== undefined) this.error = error
      this.locationFresh = this.map?.locationFresh || false
      this.lastLocation = this.map?.lastLocation || null
    }));
    this.map.update(this.data, this.stale)
  },
  beforeUnmount() {
    this.map.close()
  },
  watch: {
    data(value) {
      this.map?.update(value, this.stale)
    }, stale(value) {
      this.map?.update(this.data, value)
    }
  },
  template: `<section class="gx-navigation-map" aria-label="Interactive navigation map">
    <canvas tabindex="0" ref="canvas" aria-label="Drag to pan the map" />
    <div v-if="!locationFresh && lastLocation" class="gx-navigation-map__last">Last known position · waiting for GPS</div>
    <div class="gx-navigation-map__controls">
    <button class="gx-btn" @click="map.changeZoom(1)" aria-label="Zoom in">+</button>
    <button class="gx-btn" @click="map.changeZoom(-1)" aria-label="Zoom out">−</button>
    <button class="gx-btn" @click="map.recenter()">Recenter</button>
    </div>
    <GxNotice v-if="error" tone="danger">{{error}}</GxNotice>
    <a class="gx-navigation-map__logo" href="https://www.mapbox.com/" target="_blank" rel="noopener noreferrer" aria-label="Mapbox">
    </a>
    <div class="gx-navigation-map__credits">
    <a href="https://www.mapbox.com/about/maps/" target="_blank" rel="noopener noreferrer">© Mapbox</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap</a> · <a href="https://apps.mapbox.com/feedback/" target="_blank" rel="noopener noreferrer">Improve this map</a>
    </div>
    </section>`
}
