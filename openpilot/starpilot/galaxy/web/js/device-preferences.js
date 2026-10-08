import { GxState } from "./state.js"
import { DriveStatePanel } from "./drive-state.js"
export const DEVICE_PAGES = Object.freeze({})
export function devicePage(path) { return null }
export const DevicePreferencesPage = {
  components: { GxState, DriveStatePanel },
  props: { mode: { type: String, required: true }, go: { type: Function, required: true } },
  template: `<section class="gx-driving" aria-label="Force Drive State"><DriveStatePanel v-if="mode === 'local'" /><GxState v-else>Force Drive State is available on your connected device.</GxState></section>`,
}
