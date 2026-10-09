#!/usr/bin/env python3
"""Add a GATT peripheral beside StarPilot's existing Bluetooth service."""
import argparse
import asyncio
import base64
import json
import logging
import os
from pathlib import Path
import secrets
import signal
import struct
import time

from dbus_next import BusType, DBusError, Variant
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method

from protocol import Assembler, INFO_UUID, RX_UUID, SERVICE_UUID, TX_UUID, open_message, packets, seal
from proxy import GalaxyProxy, error_response

ROOT = "/link/galaxy/ble"
SERVICE_PATH = ROOT + "/service0"
GATT_SERVICE = "org.bluez.GattService1"
GATT_CHAR = "org.bluez.GattCharacteristic1"
LOG = logging.getLogger("galaxy-ble")


class Session:
    def __init__(self):
        self.challenge = secrets.token_bytes(16)
        self.counter = 0
        self.assembler = Assembler()
        self.response = []
        self.index = 0
        self.busy = False
        self.last_seen = time.monotonic()
        self.task = None
        self.packet_size = 20

    def close(self):
        if self.task:
            self.task.cancel()


class Gateway:
    def __init__(self, key, proxy):
        self.key = key
        self.proxy = proxy
        self.sessions = {}

    def session(self, options, fresh=False):
        device = options.get("device")
        if not device or not isinstance(device.value, str):
            raise DBusError("org.bluez.Error.NotAuthorized", "A device identity is required")
        path = device.value
        for old_path, state in list(self.sessions.items()):
            if time.monotonic() - state.last_seen > 180:
                state.close()
                del self.sessions[old_path]
        if fresh and path in self.sessions:
            self.sessions.pop(path).close()
        if path not in self.sessions:
            if len(self.sessions) >= 4:
                raise DBusError("org.bluez.Error.InProgress", "Too many sessions")
            self.sessions[path] = Session()
        state = self.sessions[path]
        state.last_seen = time.monotonic()
        mtu = int(options.get("mtu", Variant("q", 23)).value)
        state.packet_size = min(180, max(20, mtu - 3))
        return state

    def write(self, value, options):
        state = self.session(options)
        if options.get("offset", Variant("q", 0)).value:
            raise DBusError("org.bluez.Error.InvalidOffset", "Long writes are not used")
        try:
            if len(value) == 5 and value[0] == 2:
                sequence = struct.unpack(">I", value[1:])[0]
                if state.response and sequence == state.index:
                    state.index += 1
                    if state.index == len(state.response):
                        state.response = []
                        state.index = 0
                        state.busy = False
                else:
                    raise ValueError("Unexpected acknowledgement")
                return
            if state.busy:
                raise DBusError("org.bluez.Error.InProgress", "Previous response has not been acknowledged")
            data = state.assembler.add(bytes(value))
            if data is not None:
                state.busy = True
                state.task = asyncio.create_task(self.process(state, data))
        except ValueError as e:
            state.assembler.reset()
            raise DBusError("org.bluez.Error.InvalidValueLength", str(e))

    def read(self, options):
        state = self.session(options)
        if options.get("offset", Variant("q", 0)).value:
            raise DBusError("org.bluez.Error.InvalidOffset", "Packets fit inside the negotiated MTU")
        return state.response[state.index] if state.response else b"\x00"

    async def process(self, state, data):
        try:
            request = open_message(data, self.key, "request")
            counter = request.get("counter")
            if request.get("session") != state.challenge.hex() or type(counter) is not int or counter <= state.counter:
                raise ValueError("Invalid session or replayed request")
            if not isinstance(request.get("id"), str) or len(request["id"]) > 64:
                raise ValueError("Invalid request identifier")
            state.counter = counter  # Consume before invoking any mutating endpoint.
            response = await asyncio.to_thread(self.proxy.handle, request)
            response["session"] = state.challenge.hex()
            response["counter"] = counter
            state.response = list(packets(seal(response, self.key, "response"), state.packet_size))
            state.index = 0
        except asyncio.CancelledError:
            raise
        except Exception:
            # No unauthenticated error oracle; never log payloads or keys.
            LOG.warning("Rejected invalid or unauthenticated BLE message")
            state.busy = False
        finally:
            state.task = None


class GattService(ServiceInterface):
    def __init__(self):
        super().__init__(GATT_SERVICE)

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return SERVICE_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> 'b':
        return True

    def props(self):
        return {"UUID": Variant("s", self.UUID), "Primary": Variant("b", True)}


class Characteristic(ServiceInterface):
    def __init__(self, uuid, flags, gateway, kind):
        super().__init__(GATT_CHAR)
        self.uuid = uuid
        self.flags = flags
        self.gateway = gateway
        self.kind = kind

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return self.uuid

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> 'o':
        return SERVICE_PATH

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> 'as':
        return self.flags

    @method()
    def ReadValue(self, options: 'a{sv}') -> 'ay':
        if self.kind == "info":
            if options.get("offset", Variant("q", 0)).value:
                raise DBusError("org.bluez.Error.InvalidOffset", "Invalid offset")
            return b"\x01" + self.gateway.session(options, fresh=True).challenge
        if self.kind == "tx":
            return self.gateway.read(options)
        raise DBusError("org.bluez.Error.NotSupported", "Write-only characteristic")

    @method()
    def WriteValue(self, value: 'ay', options: 'a{sv}'):
        if self.kind != "rx":
            raise DBusError("org.bluez.Error.NotSupported", "Read-only characteristic")
        self.gateway.write(value, options)

    def props(self):
        return {"UUID": Variant("s", self.UUID), "Service": Variant("o", self.Service), "Flags": Variant("as", self.Flags)}


class Application(ServiceInterface):
    def __init__(self, objects):
        super().__init__("org.freedesktop.DBus.ObjectManager")
        self.objects = objects

    @method()
    def GetManagedObjects(self) -> 'a{oa{sa{sv}}}':
        return {path: {interface.name: interface.props()} for path, interface in self.objects.items()}


class Advertisement(ServiceInterface):
    def __init__(self):
        super().__init__("org.bluez.LEAdvertisement1")

    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> 's':
        return "peripheral"

    @dbus_property(access=PropertyAccess.READ)
    def ServiceUUIDs(self) -> 'as':
        return [SERVICE_UUID]

    @dbus_property(access=PropertyAccess.READ)
    def LocalName(self) -> 's':
        return "Galaxy"

    @method()
    def Release(self):
        LOG.info("BLE advertisement released")


def create_key(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    key = secrets.token_bytes(32)
    with os.fdopen(fd, "w") as f:
        json.dump({"key": key.hex()}, f)
    return key


async def serve(args):
    key_path = Path(args.key_file)
    key = bytes.fromhex(json.loads(key_path.read_text())["key"])
    if len(key) != 32:
        raise ValueError("Pairing key must be 32 bytes")
    if key_path.stat().st_mode & 0o077:
        raise ValueError("Pairing key file must have permissions 600")
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    gateway = Gateway(key, GalaxyProxy(args.galaxy_port))
    objects = {
        SERVICE_PATH: GattService(),
        SERVICE_PATH + "/rx": Characteristic(RX_UUID, ["write"], gateway, "rx"),
        SERVICE_PATH + "/tx": Characteristic(TX_UUID, ["read"], gateway, "tx"),
        SERVICE_PATH + "/info": Characteristic(INFO_UUID, ["read"], gateway, "info"),
    }
    bus.export(ROOT, Application(objects))
    for path, interface in objects.items():
        bus.export(path, interface)
    ad_path = ROOT + "/advertisement"
    bus.export(ad_path, Advertisement())
    introspection = await bus.introspect("org.bluez", "/")
    manager = bus.get_proxy_object("org.bluez", "/", introspection).get_interface("org.freedesktop.DBus.ObjectManager")
    managed = await manager.call_get_managed_objects()
    adapters = [path for path, interfaces in managed.items()
                if "org.bluez.GattManager1" in interfaces and "org.bluez.LEAdvertisingManager1" in interfaces]
    if args.adapter:
        adapters = [p for p in adapters if p.endswith("/" + args.adapter)]
    if not adapters:
        raise RuntimeError("No BlueZ adapter exposes GATT server and LE advertising. Enable Bluetooth in StarPilot and inspect bluetoothctl show.")
    adapter_path = adapters[0]
    obj = bus.get_proxy_object("org.bluez", adapter_path, await bus.introspect("org.bluez", adapter_path))
    properties = obj.get_interface("org.freedesktop.DBus.Properties")
    if not (await properties.call_get("org.bluez.Adapter1", "Powered")).value:
        raise RuntimeError("Bluetooth is off. Enable it in StarPilot before starting the bridge.")
    gatt = obj.get_interface("org.bluez.GattManager1")
    advertising = obj.get_interface("org.bluez.LEAdvertisingManager1")
    await gatt.call_register_application(ROOT, {})
    try:
        await advertising.call_register_advertisement(ad_path, {})
        LOG.info("Galaxy BLE bridge ready on %s; forwarding to localhost:%s", adapter_path, args.galaxy_port)
        stopped = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stopped.set)
        await stopped.wait()
    finally:
        for state in gateway.sessions.values():
            state.close()
        try:
            await advertising.call_unregister_advertisement(ad_path)
        except Exception:
            pass
        try:
            await gatt.call_unregister_application(ROOT)
        finally:
            bus.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", default="/data/galaxy-ble/pairing.json")
    parser.add_argument("--galaxy-port", type=int, default=8082)
    parser.add_argument("--adapter", help="Optional adapter, e.g. hci0")
    parser.add_argument("--init-key", action="store_true", help="Create a private pairing key and print it once")
    args = parser.parse_args()
    if args.init_key:
        print(create_key(Path(args.key_file)).hex())
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(serve(args))


if __name__ == "__main__":
    main()
