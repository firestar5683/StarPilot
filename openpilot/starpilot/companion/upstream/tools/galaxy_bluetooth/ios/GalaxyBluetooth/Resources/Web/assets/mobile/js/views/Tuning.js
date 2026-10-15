import { LateralTuningPanel } from "../components/LateralTuningPanel.js"
import { GalaxyTabs } from "../components/GalaxyTabs.js"
import { Plots } from "./Plots.js"
import { TestingGround } from "./TestingGround.js"
import { useTabRouting } from "../composables.js"

const TABS = {
  lateral: "Lateral Tuning",
  plots: "Plots",
  testing: "Testing Ground",
}

export const Tuning = {
  name: "Tuning",
  components: { LateralTuningPanel, Plots, TestingGround, GalaxyTabs },
  setup() {
    return useTabRouting("/tuning", { lateral: "lateral", plots: "plots", testing: "testing" })
  },
  data() { return { TABS } },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0;">Tuning, Plots & Testing</h2>

      <GalaxyTabs :items="TABS" :active="tab" @select="selectTab" />

      <template v-if="tab === 'lateral'">
        <LateralTuningPanel />
      </template>

      <template v-else-if="tab === 'plots'">
        <Plots :embedded="true" />
      </template>

      <template v-else>
        <TestingGround :embedded="true" />
      </template>
    </div>
  `,
}
