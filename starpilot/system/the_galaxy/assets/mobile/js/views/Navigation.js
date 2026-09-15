import { NavigationDestinationPanel } from "../components/NavigationDestinationPanel.js?v=nav-destination-4"
import { MapsPanel } from "../components/MapsPanel.js"
import { NavigationKeysPanel } from "../components/NavigationKeysPanel.js"
import { SpeedLimitsPanel } from "../components/SpeedLimitsPanel.js"
import { GalaxyTabs } from "../components/GalaxyTabs.js"
import { useTabRouting } from "../composables.js"

const TABS = {
  nav: "Destination",
  maps: "Maps",
  keys: "App Keys",
  speeds: "Speed Limits",
}

export const Navigation = {
  name: "Navigation",
  components: { NavigationDestinationPanel, MapsPanel, NavigationKeysPanel, SpeedLimitsPanel, GalaxyTabs },
  data() { return { TABS } },
  setup() {
    return useTabRouting("/navigation", {
      nav: "", maps: "maps", keys: "keys", speeds: "speeds",
    })
  },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0;">Navigation & Maps</h2>
      <GalaxyTabs :items="TABS" :active="tab" @select="selectTab" />
      <template v-if="tab === 'nav'"><NavigationDestinationPanel /></template>
      <template v-if="tab === 'maps'"><MapsPanel /></template>
      <template v-if="tab === 'keys'"><NavigationKeysPanel /></template>
      <template v-if="tab === 'speeds'"><SpeedLimitsPanel /></template>
    </div>
  `,
}
