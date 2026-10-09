#!/usr/bin/env python3
"""Read-only check of the on-device BlueZ and Galaxy prerequisites."""
import asyncio
import json
import urllib.request

from dbus_next import BusType
from dbus_next.aio import MessageBus


async def main():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        obj = bus.get_proxy_object("org.bluez", "/", await bus.introspect("org.bluez", "/"))
        objects = await obj.get_interface("org.freedesktop.DBus.ObjectManager").call_get_managed_objects()
        adapters = []
        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" not in interfaces:
                continue
            props = interfaces["org.bluez.Adapter1"]
            ads = interfaces.get("org.bluez.LEAdvertisingManager1", {})
            adapters.append({"adapter": path.rsplit("/", 1)[-1],
                             "powered": props.get("Powered").value if "Powered" in props else None,
                             "roles": props.get("Roles").value if "Roles" in props else [],
                             "gattServer": "org.bluez.GattManager1" in interfaces,
                             "advertising": bool(ads),
                             "supportedAdvertisements": ads.get("SupportedInstances").value if "SupportedInstances" in ads else 0,
                             "activeAdvertisements": ads.get("ActiveInstances").value if "ActiveInstances" in ads else 0})
        result = {"adapters": adapters}
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open("http://127.0.0.1:8082/api/device/status", timeout=10) as response:
                result["galaxyHTTPStatus"] = response.status
        except Exception as e:
            result["galaxyError"] = str(e)
        print(json.dumps(result, indent=2))
    finally:
        bus.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
