export function hasBluetoothName(device) {
  if (typeof device?.name !== "string") return false
  const name = device.name.trim()
  const address = name.replace(/^[[(]|[\])]$/g, "").replace(/^dev_/i, "").replace(/[:.\s_-]/g, "")
  return name.length > 0 && !/^[0-9a-f]{12}$/i.test(address)
}

// Keep discovery rows in their first-seen position while updating live state.
export class BluetoothDeviceList {
  constructor() { this.reset() }
  reset() { this.order = [] }
  update(devices) {
    const current = new Map()
    for (const device of devices) {
      if (!hasBluetoothName(device)) continue
      current.set(device.address, { ...device, name: device.name.trim() })
      if (!this.order.includes(device.address)) this.order.push(device.address)
    }
    return this.order.filter((address) => current.has(address)).map((address) => current.get(address))
  }
}
