import { GxNotice } from './notice.js'

export const bluetoothConnection = () => (globalThis.StarPilotApp || globalThis.window?.StarPilotApp)?.bluetooth?.() === true

export const BluetoothNotice = {
  name: 'BluetoothNotice',
  components: { GxNotice },
  props: { feature: { type: String, default: 'This feature' } },
  computed: { canSwitch() { return typeof (globalThis.StarPilotApp || globalThis.window?.StarPilotApp)?.connectionOptions === 'function' } },
  methods: { connections() { (globalThis.StarPilotApp || globalThis.window?.StarPilotApp)?.connectionOptions?.() } },
  template: `<GxNotice class="gx-alert--bluetooth" tone="info" icon="bi-bluetooth" :title="feature">
    Not available over Bluetooth. Connect using Galaxy Wi-Fi or LAN to use this feature.
    <slot />
    <button v-if="canSwitch" type="button" class="gx-btn gx-btn--tonal" @click="connections">Connection options</button>
  </GxNotice>`,
}
