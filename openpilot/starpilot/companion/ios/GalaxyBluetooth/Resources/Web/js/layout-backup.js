// A portable copy of the single OnroadCustomizations document, not a Params backup.
const FORMAT = "starpilot-visual-layout"
const VERSION = 1
export const MAX_LAYOUT_BACKUP_BYTES = 32768

const K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
])
const INITIAL = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
  0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
const right = (value, count) => (value >>> count) | (value << (32 - count))

// Local Galaxy can be served over plain HTTP, where Web Crypto is unavailable.
function sha256Portable(bytes) {
  const padded = new Uint8Array(Math.ceil((bytes.length + 9) / 64) * 64)
  padded.set(bytes)
  padded[bytes.length] = 0x80
  const view = new DataView(padded.buffer)
  const bits = bytes.length * 8
  view.setUint32(padded.length - 8, Math.floor(bits / 0x100000000))
  view.setUint32(padded.length - 4, bits >>> 0)
  const state = INITIAL.slice()
  const words = new Uint32Array(64)
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i++) words[i] = view.getUint32(offset + i * 4)
    for (let i = 16; i < 64; i++) {
      const x = words[i - 15], y = words[i - 2]
      const s0 = right(x, 7) ^ right(x, 18) ^ (x >>> 3)
      const s1 = right(y, 17) ^ right(y, 19) ^ (y >>> 10)
      words[i] = (words[i - 16] + s0 + words[i - 7] + s1) >>> 0
    }
    let [a, b, c, d, e, f, g, h] = state
    for (let i = 0; i < 64; i++) {
      const s1 = right(e, 6) ^ right(e, 11) ^ right(e, 25)
      const choose = (e & f) ^ (~e & g)
      const t1 = (h + s1 + choose + K[i] + words[i]) >>> 0
      const s0 = right(a, 2) ^ right(a, 13) ^ right(a, 22)
      const majority = (a & b) ^ (a & c) ^ (b & c)
      const t2 = (s0 + majority) >>> 0
      h = g; g = f; f = e; e = (d + t1) >>> 0
      d = c; c = b; b = a; a = (t1 + t2) >>> 0
    }
    state[0] = (state[0] + a) >>> 0; state[1] = (state[1] + b) >>> 0
    state[2] = (state[2] + c) >>> 0; state[3] = (state[3] + d) >>> 0
    state[4] = (state[4] + e) >>> 0; state[5] = (state[5] + f) >>> 0
    state[6] = (state[6] + g) >>> 0; state[7] = (state[7] + h) >>> 0
  }
  return state.map((word) => word.toString(16).padStart(8, "0")).join("")
}

export async function sha256(value, cryptoSource = globalThis.crypto) {
  const bytes = new TextEncoder().encode(value)
  if (!cryptoSource?.subtle) return sha256Portable(bytes)
  const digest = await cryptoSource.subtle.digest("SHA-256", bytes)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("")
}

function body(document) {
  if (!document || typeof document !== "object" || Array.isArray(document)) throw new Error("Visual layout is unavailable.")
  return { format: FORMAT, version: VERSION, document }
}

export async function encodeLayoutBackup(document, cryptoSource = globalThis.crypto) {
  const content = body(document)
  const sha256Value = await sha256(JSON.stringify(content), cryptoSource)
  const encoded = JSON.stringify({ ...content, sha256: sha256Value }) + "\n"
  if (new TextEncoder().encode(encoded).length > MAX_LAYOUT_BACKUP_BYTES) throw new Error("Visual layout backup is too large.")
  return encoded
}

export async function decodeLayoutBackup(text, cryptoSource = globalThis.crypto) {
  if (typeof text !== "string" || new TextEncoder().encode(text).length > MAX_LAYOUT_BACKUP_BYTES) {
    throw new Error("Visual layout backup is too large or unreadable.")
  }
  let parsed
  try { parsed = JSON.parse(text) } catch { throw new Error("Visual layout backup is not valid JSON.") }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) ||
      Object.keys(parsed).join(",") !== "format,version,document,sha256" ||
      parsed.format !== FORMAT || parsed.version !== VERSION ||
      !/^[0-9a-f]{64}$/.test(parsed.sha256) ||
      text !== JSON.stringify(parsed) + "\n") {
    throw new Error("Visual layout backup has an unsupported format.")
  }
  const content = body(parsed.document)
  if (await sha256(JSON.stringify(content), cryptoSource) !== parsed.sha256) {
    throw new Error("Visual layout backup checksum does not match.")
  }
  return parsed.document
}
