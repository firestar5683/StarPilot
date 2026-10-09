function showSnackbar(msg, level, timeout = 3500, options = {}) {
  const wrapper = document.getElementById("snackbar_wrapper")
  if (!wrapper) return

  const key = String(options?.key || "").trim()
  const replace = options?.replace !== false

  const dismissSnackbar = (snackbar) => {
    if (!snackbar) return
    if (snackbar.__hideTimer) clearTimeout(snackbar.__hideTimer)
    if (snackbar.__removeTimer) clearTimeout(snackbar.__removeTimer)
    snackbar.style.opacity = 0
    snackbar.__removeTimer = setTimeout(() => snackbar.remove(), 1000)
  }

  const setSnackbarContent = (snackbar) => {
    snackbar.innerHTML = msg
    snackbar.className = "snackbar show"
    snackbar.setAttribute("role", level === "error" ? "alert" : "status")
    snackbar.setAttribute("aria-live", level === "error" ? "assertive" : "polite")
    snackbar.setAttribute("aria-atomic", "true")
    if (level === "error") {
      snackbar.style.backgroundColor = "#f44336"
    } else {
      snackbar.style.backgroundColor = ""
    }
  }

  if (key && replace) {
    const existing = Array.from(wrapper.children).find((el) => el.dataset?.snackbarKey === key)
    if (existing) {
      setSnackbarContent(existing)
      existing.style.opacity = 1
      if (existing.__hideTimer) clearTimeout(existing.__hideTimer)
      if (existing.__removeTimer) clearTimeout(existing.__removeTimer)
      existing.__hideTimer = setTimeout(() => dismissSnackbar(existing), timeout)
      return
    }
  }

  // Ensure max 2 snackbars are visible
  if (wrapper.children.length >= 2) {
    dismissSnackbar(wrapper.children[0])
  }

  const snackbar = document.createElement("div")
  snackbar.id = `snackbar_${Math.random().toString(36).slice(5)}`
  if (key) snackbar.dataset.snackbarKey = key
  setSnackbarContent(snackbar)

  wrapper.appendChild(snackbar)
  snackbar.__hideTimer = setTimeout(() => dismissSnackbar(snackbar), timeout)
}
