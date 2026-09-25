// Pixels and sprite locations come from the actual onroad renderer, not browser widget copies.
export async function widgetArtMetadata(blob) {
  const bytes = new Uint8Array(await blob.arrayBuffer())
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  if (bytes.length < 45 || bytes.length > 4 * 1024 * 1024 ||
      ![137,80,78,71,13,10,26,10].every((value, index) => bytes[index] === value)) throw new Error("Invalid widget art")
  const text = new TextDecoder(), signature = "starpilot-widget-art\0"
  let metadata = null
  for (let offset = 8; offset + 12 <= bytes.length;) {
    const size = view.getUint32(offset), type = text.decode(bytes.subarray(offset + 4, offset + 8))
    if (size > bytes.length - offset - 12) throw new Error("Invalid widget art chunk")
    if (type === "tEXt") {
      const value = text.decode(bytes.subarray(offset + 8, offset + 8 + size))
      if (value.startsWith(signature)) {
        if (metadata || size > 8192) throw new Error("Invalid widget art metadata")
        metadata = JSON.parse(value.slice(signature.length))
      }
    }
    offset += size + 12
  }
  if (!metadata || metadata.version !== 1 || !Number.isInteger(metadata.width) || !Number.isInteger(metadata.height) ||
      metadata.width < 1 || metadata.width > 1024 || metadata.height < 1 || metadata.height > 1440 ||
      metadata.width !== view.getUint32(16) || metadata.height !== view.getUint32(20) ||
      !metadata.sprites || typeof metadata.sprites !== "object" || Array.isArray(metadata.sprites) ||
      Object.keys(metadata.sprites).length > 7) throw new Error("Invalid widget art metadata")
  for (const [id, rect] of Object.entries(metadata.sprites)) {
    if (!/^[a-z_]+$/.test(id) || !rect || ![rect.x,rect.y,rect.width,rect.height].every(Number.isInteger) ||
        rect.x < 0 || rect.y < 0 || rect.width < 1 || rect.height < 1 ||
        rect.x + rect.width > metadata.width || rect.y + rect.height > metadata.height ||
        ![rect.offsetX ?? 0, rect.offsetY ?? 0].every(value => Number.isFinite(value) && value > -1 && value <= 0)) throw new Error("Invalid widget art rectangle")
  }
  return metadata
}
