export function haptic() {
  try { globalThis.navigator?.vibrate?.(15) } catch {}
}

export function toggleHaptic(event) {
  const input = event.target
  if (input.matches?.('.gx-switch input[type="checkbox"], input[role="switch"]') &&
      !input.disabled && !input.closest('[inert]')) haptic()
}
