// Coordinates are saved in the unmirrored source camera frame. The editor is mirrored for the driver.
export const FORMATS = [[1928, 1208], [1344, 760]]
export const displaySide = (cameraSide) => cameraSide === "cameraRight" ? "Vehicle left (camera right)" :
  cameraSide === "cameraLeft" ? "Vehicle right (camera left)" : ""

export function sourcePoint(clientX, clientY, rect, width, height) {
  if (!(rect?.width > 0 && rect.height > 0) || !FORMATS.some(([w, h]) => w === width && h === height)) return null
  const x = (clientX - rect.left) / rect.width
  const y = (clientY - rect.top) / rect.height
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 1 || y < 0 || y > 1) return null
  return [Math.round((1 - x) * width), Math.round(y * height)]
}

const orient = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
const between = (a, b, c) => b >= Math.min(a, c) && b <= Math.max(a, c)
function intersects(a, b, c, d) {
  const abc = orient(a, b, c), abToD = orient(a, b, d), cda = orient(c, d, a), cdb = orient(c, d, b)
  const on = (p, q, r) => orient(p, q, r) === 0 && between(p[0], q[0], r[0]) && between(p[1], q[1], r[1])
  return on(a, c, b) || on(a, d, b) || on(c, a, d) || on(c, b, d) ||
    ((abc > 0) !== (abToD > 0) && (cda > 0) !== (cdb > 0))
}

export function validPolygon(points, width, height) {
  if (!Array.isArray(points) || points.length < 3 || points.length > 32) return false
  if (points.some((point) => !Array.isArray(point) || point.length !== 2 ||
      point.some((v) => !Number.isFinite(v)) || point[0] < 0 || point[0] > width ||
      point[1] < 0 || point[1] > height)) return false
  if (new Set(points.map((p) => `${p[0]},${p[1]}`)).size !== points.length) return false
  const area = points.reduce((sum, a, i) => {
    const b = points[(i + 1) % points.length]
    return sum + a[0] * b[1] - b[0] * a[1]
  }, 0)
  if (Math.abs(area) <= 1e-9 * width * height) return false
  for (let i = 0; i < points.length; i++) {
    for (let j = i + 2; j < points.length; j++) {
      if (i === 0 && j === points.length - 1) continue
      if (intersects(points[i], points[(i + 1) % points.length], points[j], points[(j + 1) % points.length])) return false
    }
  }
  return true
}

export function annotationDraft(width, height, cameraLeft, cameraRight) {
  if (!FORMATS.some(([w, h]) => w === width && h === height)) return null
  if (!Array.isArray(cameraLeft) || !Array.isArray(cameraRight) ||
      (!cameraLeft.length && !cameraRight.length) ||
      (cameraLeft.length && !validPolygon(cameraLeft, width, height)) ||
      (cameraRight.length && !validPolygon(cameraRight, width, height))) return null
  return { version: 1, width, height, poly_left: cameraLeft, poly_right: cameraRight }
}
