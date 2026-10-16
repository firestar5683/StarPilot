export function spawnAmbientStars(background, random = Math.random) {
  if (!background || background.querySelector(".galaxy-hero")) return 0
  for (let index = 0; index < 14; index++) {
    const star = background.ownerDocument.createElement("i")
    star.className = "galaxy-hero"
    star.style.left = `${(random() * 100).toFixed(2)}%`
    star.style.top = `${(random() * 100).toFixed(2)}%`
    star.style.animationDelay = `${(random() * 4).toFixed(2)}s`
    star.style.width = star.style.height = random() > 0.6 ? "3px" : "2px"
    background.appendChild(star)
  }
  return 14
}
