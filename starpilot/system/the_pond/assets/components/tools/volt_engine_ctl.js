import { html } from "/assets/vendor/arrow-core.js"

export function VoltEngineCtl () {
  async function engineOn () {
    const response = await fetch("/api/engine/on", { method: "POST" })
    const result = await response.json()
    showSnackbar(result.message || "Engine ON!")
  }

  async function engineOff () {
    const response = await fetch("/api/engine/off", { method: "POST" })
    const result = await response.json()
    showSnackbar(result.message || "Engine OFF!")
  }

  async function releaseControl () {
    const response = await fetch("/api/engine/release", { method: "POST" })
    const result = await response.json()
    showSnackbar(result.message || "Control Released!")
  }

  return html`
    <div class="engine-control-wrapper">
      <section class="engine-control-widget">
        <div class="engine-control-title">Engine Controls</div>
        <p class="engine-control-text">
          Force the engine on/off when the car is on.
        </p>
        <button class="engine-control-button" @click="${engineOn}">Engine ON</button>
        <button class="engine-control-button" @click="${engineOff}">Engine OFF</button>
        <button class="engine-control-button" @click="${releaseControl}">Release Control</button>
      </section>
    </div>
  `
}
