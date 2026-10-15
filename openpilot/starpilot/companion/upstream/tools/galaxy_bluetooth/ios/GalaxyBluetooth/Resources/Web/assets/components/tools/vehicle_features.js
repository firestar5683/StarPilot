import { html, reactive } from "/assets/vendor/arrow-core.js"
import { DoorControl } from "/assets/components/tools/doors.js"
import { TSKManager } from "/assets/components/tools/tsk_manager.js"

const state = reactive({
  activeTool: null,
  toolStatus: {
    doors: "untested", // untested, allowed, denied
    tsk: "untested"
  },
  loading: false
})

async function checkToolAvailability(toolName) {
  if (state.toolStatus[toolName] !== "untested") {
    state.activeTool = toolName;
    return;
  }

  state.loading = true;
  state.activeTool = toolName;

  try {
    const response = await fetch(`/api/car_features_check?tool=${toolName}`);
    const data = await response.json();
    state.toolStatus[toolName] = data.result ? "allowed" : "denied";
  } catch (error) {
    console.error("Failed to check feature availability:", error);
    state.toolStatus[toolName] = "denied";
  } finally {
    state.loading = false;
  }
}

export function VehicleFeatures() {
  return html`
    <style>
      .vf-container {
        padding: var(--padding-lg);
        max-width: var(--max-width-content);
        margin: 0 auto;
      }
      .vf-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: var(--gap-lg);
        margin-top: var(--margin-lg);
      }
      .vf-card {
        background: var(--card-bg);
        border: var(--border-width-thin) var(--border-style-base) var(--sidebar-border-color);
        border-radius: var(--border-radius-lg);
        padding: var(--padding-lg);
        cursor: pointer;
        transition: transform var(--transition-fast), box-shadow var(--transition-fast);
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
      }
      .vf-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        border-color: var(--main-fg);
      }
      .vf-card i {
        font-size: 2.5rem;
        margin-bottom: var(--margin-sm);
        color: var(--main-fg);
      }
      .vf-card h3 {
        margin: 0 0 var(--margin-xs) 0;
        font-size: var(--font-size-lg);
      }
      .vf-card p {
        margin: 0;
        font-size: var(--font-size-sm);
        color: var(--text-muted);
      }
      .vf-back {
        background: none;
        border: none;
        color: var(--main-fg);
        cursor: pointer;
        font-size: var(--font-size-base);
        display: flex;
        align-items: center;
        gap: var(--gap-sm);
        padding: 0;
        margin-bottom: var(--margin-lg);
      }
      .vf-back:hover {
        text-decoration: underline;
      }
      .vf-error {
        margin-top: var(--margin-lg);
        padding: var(--padding-base);
        background: rgba(224, 85, 119, 0.1);
        border: var(--border-width-thin) var(--border-style-base) var(--danger-fg);
        border-radius: var(--border-radius-md);
        color: var(--danger-fg);
        text-align: center;
      }
      .vf-loader {
        text-align: center;
        padding: var(--padding-xxl);
        color: var(--text-muted);
      }
    </style>

    <div class="vf-container">
      ${() => {
      if (!state.activeTool) {
        return html`
            <h1>Vehicle Specific Features</h1>
            <p style="color: var(--text-muted); margin-bottom: var(--margin-xl);">
              Select a feature below to access it. These features verify vehicle compatibility when launched.
            </p>
            <div class="vf-grid">
              <div class="vf-card" @click="${() => checkToolAvailability('doors')}">
                <i class="bi bi-door-closed"></i>
                <h3>Lock/Unlock Doors</h3>
                <p>Send lock or unlock commands remotely to your vehicle.</p>
              </div>
              <div class="vf-card" @click="${() => checkToolAvailability('tsk')}">
                <i class="bi bi-key-fill"></i>
                <h3>Toyota Security Keys</h3>
                <p>Manage and apply security keys for secOC protected devices.</p>
              </div>
            </div>
          `;
      }

      return html`
          <button class="vf-back" @click="${() => { state.activeTool = null; }}">
            <i class="bi bi-arrow-left"></i> Back to Features
          </button>

          ${() => {
          if (state.loading) {
            return html`<div class="vf-loader"><i class="bi bi-hourglass-split"></i> Verifying vehicle compatibility...</div>`;
          }

          if (state.toolStatus[state.activeTool] === "denied") {
            const toolNames = { doors: "Lock/Unlock Doors", tsk: "Toyota Security Keys" };
            return html`
                <div class="vf-error">
                  <i class="bi bi-exclamation-triangle-fill" style="font-size: 2rem; display: block; margin-bottom: var(--margin-sm);"></i>
                  <strong>${toolNames[state.activeTool]}</strong> is not supported for your current vehicle.
                </div>
              `;
          }

          if (state.activeTool === "doors") return DoorControl();
          if (state.activeTool === "tsk") return TSKManager();
          return "";
        }}
        `;
    }}
    </div>
  `;
}
