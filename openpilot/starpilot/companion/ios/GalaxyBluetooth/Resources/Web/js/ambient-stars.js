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
