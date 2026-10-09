import { GalaxyTabs } from "../components/GalaxyTabs.js"
import { useTabRouting } from "../composables.js"
import { Sentry } from "./Sentry.js"
import { Vasm } from "./Vasm.js"
import { Pip } from "./Pip.js"

const TABS = {
  sentry: "Sentry Mode",
  vasm: "V-ASM Spot Monitor",
  pip: "PiP Side Camera",
}

export const Cameras = {
  name: "Cameras",
  components: { Sentry, Vasm, Pip, GalaxyTabs },
  setup() {
    return useTabRouting("/cameras", { sentry: "sentry", vasm: "vasm", pip: "pip" })
  },
  data() { return { TABS } },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0;">Cameras & Monitoring</h2>
      <GalaxyTabs :items="TABS" :active="tab" @select="selectTab" />

      <template v-if="tab === 'sentry'">
        <Sentry />
      </template>

      <template v-else-if="tab === 'vasm'">
        <Vasm :embedded="true" />
      </template>

      <template v-else>
        <Pip :embedded="true" />
      </template>
    </div>
  `,
}
