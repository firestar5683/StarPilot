// Saved centers are pixels in the unmirrored cabin frame. Invert changes only
// the displayed crop pixels; vehicle-side selection always uses source sides.
export const FORMATS = [[1928, 1208], [1344, 760]]

export function displayPoint(center, width, invert) {
  return center === null ? null : [invert ? width - center[0] : center[0], center[1]]
}

export function sourcePoint(clientX, clientY, rect, width, height, invert) {
  if (!(rect?.width > 0 && rect.height > 0) || typeof invert !== "boolean" ||
      !FORMATS.some(([w, h]) => w === width && h === height)) return null
  const x = (clientX - rect.left) / rect.width
  const y = (clientY - rect.top) / rect.height
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 1 || y < 0 || y > 1) return null
  return [Math.round((invert ? 1 - x : x) * width), Math.round(y * height)]
}

const centerValid = (center, width, height, size) => center === null ||
  (Array.isArray(center) && center.length === 2 && center.every(Number.isInteger) &&
   center[0] - size / 2 >= 0 && center[0] + size / 2 <= width &&
   center[1] - size / 2 >= 0 && center[1] + size / 2 <= height)

export function maskDraft(width, height, cropSize, centerLeft, centerRight) {
  if (!FORMATS.some(([w, h]) => w === width && h === height) ||
      !Number.isInteger(cropSize) || cropSize < 20 || cropSize > Math.min(width, height) ||
      (centerLeft === null && centerRight === null) ||
      !centerValid(centerLeft, width, height, cropSize) ||
      !centerValid(centerRight, width, height, cropSize)) return null
  return { width, height, crop_size: cropSize, center_left: centerLeft, center_right: centerRight }
}
