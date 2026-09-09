// Shared download-confirmation dialog; longitudinal help buttons removed.
let activeDialog = null
let dialogId = 0
function installStyle() {
  if (document.getElementById("gx-feature-help-style")) return
  const style = document.createElement("style")
  style.id = "gx-feature-help-style"
  style.textContent = `
    .gx-help-dialog {box-sizing:border-box;width:min(640px,calc(100% - 24px));max-width:calc(100% - 24px);max-height:var(--gx-help-height,85dvh);margin:auto;padding:0;border:1px solid var(--outline-variant,#667085);border-radius:var(--radius-lg,18px);background:var(--background,#20252e);color:var(--on-surface,#edf0f5);box-shadow:0 16px 64px #0008;overflow:auto;overscroll-behavior:contain;overflow-wrap:anywhere;font-family:inherit}
    .gx-help-dialog::backdrop {background:#0009}
    .gx-help-dialog__heading {margin:0;padding:20px 20px 8px;font-size:1.25rem;line-height:1.35}
    .gx-help-dialog__body {padding:0 20px;line-height:1.6}
    .gx-help-dialog__body p {white-space:pre-line;margin:12px 0}
    .gx-help-dialog__body h4 {font-size:1rem;margin:20px 0 8px}
    .gx-help-dialog__actions {display:flex;justify-content:flex-end;flex-wrap:wrap;gap:12px;padding:16px 20px;position:sticky;bottom:0;background:var(--background,#20252e);border-top:1px solid var(--outline-variant,#667085)}
    .gx-help-dialog__actions button {min-height:44px}
  `
  document.head.appendChild(style)
}

// Native modal provides inert background, Escape and focus restoration. No settings writes.
export function openGalaxyHelpDialog({ title, paragraphs = [], troubleshooting = [], confirmLabel = "Close", cancelLabel = "" }) {
  installStyle()
  activeDialog?.()
  return new Promise(resolve => {
    const opener = document.activeElement
    const dialog = document.createElement("dialog")
    dialog.className = "gx-help-dialog"
    dialog.setAttribute("aria-modal", "true")
    const titleId = `gx-help-title-${++dialogId}`
    dialog.setAttribute("aria-labelledby", titleId)
    const heading = document.createElement("h3")
    heading.id = titleId
    heading.className = "gx-help-dialog__heading"
    heading.textContent = title
    const body = document.createElement("div")
    body.className = "gx-help-dialog__body"
    const paragraph = text => { const p = document.createElement("p"); p.textContent = text; body.appendChild(p) }
    paragraphs.forEach(paragraph)
    if (troubleshooting.length) {
      const h = document.createElement("h4"); h.textContent = "Troubleshooting"; body.appendChild(h)
      troubleshooting.forEach(paragraph)
    }
    const actions = document.createElement("div")
    actions.className = "gx-help-dialog__actions"
    let settled = false
    const finish = result => {
      if (settled) return
      settled = true
      window.removeEventListener("hashchange", cancel)
      window.removeEventListener("resize", resize)
      window.visualViewport?.removeEventListener("resize", resize)
      if (activeDialog === cancel) activeDialog = null
      dialog.close()
      dialog.remove()
      if (opener?.isConnected) opener.focus({ preventScroll: true })
      resolve(result)
    }
    const cancel = () => finish(false)
    const resize = () => {
      // CSS zoom changes available CSS-pixel space independently of device scale.
      let zoom = 1
      for (let node = document.body; node; node = node.parentElement) zoom *= parseFloat(getComputedStyle(node).zoom) || 1
      dialog.style.setProperty("--gx-help-height", `${Math.max(100, ((window.visualViewport?.height || innerHeight) - 24) / zoom)}px`)
    }
    const button = (label, result, secondary) => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = label
      b.className = `gx-btn${secondary ? " gx-btn--tonal" : ""}`
      b.addEventListener("click", () => finish(result)); actions.appendChild(b)
    }
    if (cancelLabel) button(cancelLabel, false, true)
    button(confirmLabel, true, false)
    dialog.append(heading, body, actions)
    dialog.addEventListener("cancel", event => { event.preventDefault(); cancel() })
    dialog.addEventListener("click", event => {
      const box = dialog.getBoundingClientRect()
      if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) cancel()
    })
    dialog.addEventListener("keydown", event => {
      if (event.key !== "Tab") return
      const buttons = [...actions.querySelectorAll("button")]
      const first = buttons[0], last = buttons.at(-1)
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    })
    window.addEventListener("hashchange", cancel)
    window.addEventListener("resize", resize)
    window.visualViewport?.addEventListener("resize", resize)
    document.body.appendChild(dialog)
    activeDialog = cancel
    resize()
    dialog.showModal()
    actions.querySelector("button").focus({ preventScroll: true })
  })
}
