// Keep unsaved drafts and pending saves on the page, including during host live reload.
export function guardUnload(shouldBlock) {
  const listener = event => {
    if (shouldBlock()) { event.preventDefault(); event.returnValue = "" }
  }
  window.addEventListener("beforeunload", listener)
  return () => window.removeEventListener("beforeunload", listener)
}
