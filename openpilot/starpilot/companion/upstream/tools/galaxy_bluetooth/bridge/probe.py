#!/usr/bin/env python3
"""Read-only check of the on-device BlueZ and Galaxy prerequisites."""
import asyncio
import json
from pathlib import Path
import platform
import shutil
import subprocess
import urllib.request

from dbus_next import BusType
from dbus_next.aio import MessageBus


def live_encoder_check():
    executable = shutil.which("ffmpeg")
    if not executable:
        return {"available": False, "error": "ffmpeg not found"}
    try:
        result = subprocess.run([
            executable, "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
            "-pix_fmt", "rgba", "-s:v", "960x480", "-r", "20", "-i", "pipe:0",
            "-frames:v", "1", "-an", "-c:v", "mjpeg", "-q:v", "5", "-threads", "1",
            "-f", "rawvideo", "pipe:1",
        ], input=bytes(960 * 480 * 4), capture_output=True, timeout=15)
        valid = result.returncode == 0 and result.stdout.startswith(b"\xff\xd8") and result.stdout.endswith(b"\xff\xd9")
        report = {"path": executable, "available": valid}
        if not valid:
            report["error"] = result.stderr.decode("utf-8", errors="replace")[-1000:] or "No complete JPEG produced"
        return report
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"path": executable, "available": False, "error": str(error)}


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
        try:
            model = Path("/sys/firmware/devicetree/base/model").read_text().strip("\x00\n")
        except OSError:
            model = "unknown"
        result = {"model": model, "python": platform.python_version(), "adapters": adapters,
                  "liveEncoder": live_encoder_check()}
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
