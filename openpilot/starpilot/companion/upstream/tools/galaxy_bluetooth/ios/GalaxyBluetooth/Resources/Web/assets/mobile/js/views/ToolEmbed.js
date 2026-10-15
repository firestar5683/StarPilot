import { store } from "../store.js"
import { GalaxyEmbed } from "../components/GalaxyEmbed.js"

export const ToolEmbed = {
  name: "ToolEmbed",
  components: { GalaxyEmbed },
  computed: {
    src() { return store.params.src || "/tools" },
    title() {
      const map = {
        "/manage_models": "Model Manager",
        "/model_laboratory": "Model Laboratory",
        "/galaxy": "Galaxy",
        "/sentry": "Sentry Mode",
        "/plots": "Live Plots",
        "/download_speed_limits": "Download Speed Limits",
        "/testing_ground": "Testing Ground",
        "/theme_maker": "Theme Maker",
        "/troubleshoot": "Troubleshoot",
        "/manage_tmux": "Tmux Log",
        "/manage_toggles": "Backup and Restore",
        "/manage_updates": "Software",
        "/manage_error_logs": "Error Logs",
        "/bluetooth": "Bluetooth",
        "/wheel-controls": "Controllers",
        "/vehicle_features": "Vehicle Features",
        "/manage_doors": "Lock/Unlock Doors",
        "/manage_tsk": "Toyota Security Keys",
        "/set_navigation_destination": "Navigation Destination",
        "/manage_navigation_keys": "App Keys",
        "/manage_maps": "Maps",
      }
      return map[this.src] || "Tool"
    },
  },
  template: `
    <div class="gx-view">
      <div class="gx-section__header" style="padding: var(--sp-3) var(--sp-4);">
        <i class="bi bi-grid"></i>
        <span class="gx-section__title">{{ title }}</span>
      </div>
      <GalaxyEmbed :src="src" :title="title" forward-nav />
    </div>
  `,
}
