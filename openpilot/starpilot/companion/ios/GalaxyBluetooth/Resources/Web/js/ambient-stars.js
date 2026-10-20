const STAR_COUNT = 14

export function spawnAmbientStars(background, random = Math.random) {
  if (!background || background.querySelector(".galaxy-hero")) return 0
  for (let index = 0; index < STAR_COUNT; index++) {
    const star = background.ownerDocument.createElement("i")
    star.className = "galaxy-hero"
    star.style.left = `${(random() * 100).toFixed(2)}%`
    star.style.top = `${(random() * 100).toFixed(2)}%`
    star.style.animationDelay = `${(random() * 4).toFixed(2)}s`
    star.style.setProperty("--galaxy-star-core", random() > 0.6 ? "3px" : "2px")
    background.appendChild(star)
  }
  return STAR_COUNT
}

export function pauseStarsOnSlowFirefoxScroll(background) {
  const ua = navigator.userAgent
  if (!background || !((/Android/.test(ua) && /Firefox\//.test(ua)) || /FxiOS\//.test(ua)) ||
      !matchMedia("(pointer: coarse)").matches) return

  let frame = 0
  let lastFrame = 0
  let lastScroll = 0
  let elapsed = 0
  let samples = 0
  const starsHidden = () => document.hidden || document.querySelector(".gx-dialog[open], .gx-underlay, .gx-drawer.open, .gx-route-workspace")

  const sample = (now) => {
    if (starsHidden()) { frame = lastFrame = elapsed = samples = 0; return }
    if (lastFrame && now - lastFrame < 150) {
      elapsed += now - lastFrame
      samples++
      if (elapsed >= 1000) {
        if (samples * 1000 / elapsed < 30) {
          background.classList.add("galaxy-stars-paused")
          window.removeEventListener("scroll", onScroll, true)
          return
        }
        elapsed = samples = 0
      }
    }
    lastFrame = now
    frame = now - lastScroll < 150 ? requestAnimationFrame(sample) : 0
  }

  const onScroll = () => {
    if (starsHidden()) return
    lastScroll = performance.now()
    if (!frame) frame = requestAnimationFrame(sample)
  }
  window.addEventListener("scroll", onScroll, { passive: true, capture: true })
}
