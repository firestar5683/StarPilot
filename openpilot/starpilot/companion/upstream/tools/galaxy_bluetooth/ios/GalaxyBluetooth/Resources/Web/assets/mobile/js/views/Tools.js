import { navigate, toolHref } from "../store.js"

const TOOLS = [
  { name: "Bluetooth", link: "/bluetooth", icon: "bi-bluetooth", desc: "Pair devices, controllers, & audio" },
  { name: "Cameras & Monitoring", link: "/cameras", icon: "bi-camera-video", desc: "Sentry, PiP side camera, & V-ASM spot monitor" },
  { name: "Galaxy & App Install", link: "/galaxy", icon: "bi-globe2", desc: "Remote access, pairing, & app install" },  
  { name: "Logs & Diagnostics", link: "/logs", icon: "bi-exclamation-triangle", desc: "Error logs, tmux, troubleshoot" },
  { name: "Model Manager", link: "/manage_models", icon: "bi-cpu", desc: "Install/swap models" },
  { name: "Model Laboratory", link: "/model_laboratory", icon: "bi-bezier2", desc: "Pair lateral and longitudinal models" },
  { name: "Navigation & Maps", link: "/navigation", icon: "bi-map", desc: "Offline maps & destinations" },
  { name: "System Tools", link: "/system", icon: "bi-arrow-repeat", desc: "Backup, restore, updates" },
  { name: "Theme Maker", link: "/theme_maker", icon: "bi-palette-fill", desc: "Customize the look" },
  { name: "Tuning, Plots & Testing", link: "/tuning", icon: "bi-sign-turn-right", desc: "Steering & speed tuning, live plots, testing grounds" },
  { name: "Vehicle Controls", link: "/vehicle", icon: "bi-car-front", desc: "Vehicle features" },
].sort((a, b) => a.name.localeCompare(b.name))

export const Tools = {
  name: "Tools",
  data() { return { TOOLS } },
  methods: {
    open(t) {
      navigate(toolHref(t.link))
    },
  },
  template: `
    <div>
      <h2 style="margin-top:0;">Tools</h2>
      <div class="gx-grid">
        <button v-for="t in TOOLS" :key="t.link" type="button" class="gx-tile" @click="open(t)">
          <i class="bi" :class="t.icon"></i>
          <span>{{ t.name }}</span>
          <small style="color: var(--text-muted);">{{ t.desc }}</small>
        </button>
      </div>
    </div>
  `,
}
