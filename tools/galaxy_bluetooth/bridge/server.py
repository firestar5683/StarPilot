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

from protocol import (Assembler, INFO_UUID, RX_UUID, SERVICE_UUID, TX_UUID, NOTIFY_UUID,
                      NOTIFICATION_WINDOW, open_message, packets, seal, stream_tag, notification_packets)
from proxy import GalaxyProxy, error_response
from pairing import load_key
from setup_health import write_ready, clear_ready

ROOT = "/link/galaxy/ble"
SERVICE_PATH = ROOT + "/service0"
GATT_SERVICE = "org.bluez.GattService1"
GATT_CHAR = "org.bluez.GattCharacteristic1"
LOG = logging.getLogger("galaxy-ble")
NOTIFICATION_ACK_TIMEOUT = 15


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
        self.read_stream = False
        self.response_started = 0
        self.notification_stream = False
        self.notification_tag = b""
        self.notification_ack = asyncio.Event()
        self.notification_expected_ack = None
        self.notification_task = None
        self.closed = False

    def close(self):
        self.closed = True
        if self.task:
            self.task.cancel()
        if self.notification_task:
            self.notification_task.cancel()


class Gateway:
    def __init__(self, key, proxy, key_path=None):
        self.key = key
        self.key_path = key_path
        self.proxy = proxy
        self.sessions = {}
        self.notifier = None
        self.notification_lock = asyncio.Lock()

    def refresh_key(self):
        if self.key_path is None:
            return
        try:
            key = load_key(self.key_path)
        except Exception:
            # Fail closed if the local credential is removed or invalid.
            key = None
        if key != self.key:
            for state in self.sessions.values():
                state.close()
            self.sessions.clear()
            self.key = key
            LOG.info("Pairing credentials changed; Bluetooth sessions revoked")
        if key is None:
            raise DBusError("org.bluez.Error.NotAuthorized", "Pairing credentials unavailable")

    async def watch_key(self):
        while True:
            await asyncio.sleep(0.5)
            try:
                self.refresh_key()
            except DBusError:
                pass

    def session(self, options, fresh=False):
        self.refresh_key()
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
        if "mtu" in options:
            state.packet_size = min(512, max(20, int(options["mtu"].value) - 3))
        return state

    def write(self, value, options):
        state = self.session(options)
        if options.get("offset", Variant("q", 0)).value:
            raise DBusError("org.bluez.Error.InvalidOffset", "Long writes are not used")
        try:
            if len(value) == 13 and value[0] == 4:
                sequence = struct.unpack(">I", value[9:])[0]
                if (not state.notification_stream or not state.response or bytes(value[1:9]) != state.notification_tag
                        or sequence != state.notification_expected_ack or state.index != sequence + 1
                        or state.notification_ack.is_set()):
                    raise ValueError("Unexpected notification acknowledgement")
                state.notification_ack.set()
                state.notification_expected_ack = None
                if state.index == len(state.response):
                    self.acknowledged(state)
                return
            if len(value) == 5 and value[0] == 2:
                sequence = struct.unpack(">I", value[1:])[0]
                if state.notification_stream:
                    raise ValueError("Notification responses require a tagged acknowledgement")
                elif state.read_stream and state.response:
                    if state.index != len(state.response) or sequence != len(state.response) - 1:
                        raise ValueError("Unexpected stream acknowledgement")
                    self.acknowledged(state)
                elif state.response and sequence == state.index:
                    state.index += 1
                    if state.index == len(state.response):
                        self.acknowledged(state)
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

    def acknowledged(self, state):
        LOG.info("Response delivered: %d packets in %.2fs (%s)", len(state.response),
                 time.monotonic() - state.response_started,
                 "notification stream" if state.notification_stream else "read stream" if state.read_stream else "per-packet ACK")
        state.response = []
        state.index = 0
        state.busy = False

    def read(self, options):
        state = self.session(options)
        if options.get("offset", Variant("q", 0)).value:
            raise DBusError("org.bluez.Error.InvalidOffset", "Packets fit inside the negotiated MTU")
        if state.notification_stream:
            return b"\x00"
        if not state.response or state.index >= len(state.response):
            return b"\x00"
        packet = state.response[state.index]
        if state.read_stream:
            # ACK once after the read stream is verified.
            state.index += 1
        return packet

    async def process(self, state, data):
        started = time.monotonic()
        try:
            self.refresh_key()
            if state.closed:
                return
            request = open_message(data, self.key, "request")
            counter = request.get("counter")
            if request.get("session") != state.challenge.hex() or type(counter) is not int or counter <= state.counter:
                raise ValueError("Invalid session or replayed request")
            if not isinstance(request.get("id"), str) or len(request["id"]) > 64:
                raise ValueError("Invalid request identifier")
            if counter > 0xffffffffffffffff:
                raise ValueError("Invalid counter")
            fast = request.get("responseCodec") == 2
            notify = fast and request.get("responseFlow") == "notify-window8"
            if notify and (self.notifier is None or not self.notifier.notifying):
                raise ValueError("Subscribe to notifications before requesting that response flow")
            state.counter = counter  # Consume before invoking any mutating endpoint.
            response = await asyncio.to_thread(self.proxy.handle, request)
            self.refresh_key()
            if state.closed:
                return
            response["session"] = state.challenge.hex()
            response["counter"] = counter
            state.notification_stream = notify
            state.notification_tag = stream_tag(state.challenge.hex(), counter) if notify else b""
            state.read_stream = fast and request.get("responseFlow") == "read-stream"
            frame = seal(response, self.key, "response", compact_body=fast)
            size = state.packet_size if fast else min(180, state.packet_size)
            state.response = list(notification_packets(frame, state.notification_tag, size) if notify else packets(frame, size))
            state.index = 0
            state.response_started = time.monotonic()
            LOG.info("Response prepared: %d bytes, %d packets, ATT payload %d, %.2fs (%s)",
                     len(frame), len(state.response), size, time.monotonic() - started,
                     "notification stream" if notify else "read stream" if state.read_stream else "per-packet ACK")
            if notify:
                state.notification_task = asyncio.create_task(self.push_response(state))
        except asyncio.CancelledError:
            raise
        except Exception:
            # No unauthenticated error oracle; never log payloads or keys.
            LOG.warning("Rejected invalid or unauthenticated BLE message")
            state.busy = False
        finally:
            state.task = None

    async def push_response(self, state):
        response = state.response
        try:
            # Serialize broadcasts and tag each client’s frames.
            async with self.notification_lock:
                while state.response is response and response and not state.closed:
                    if self.notifier is None or not self.notifier.notifying:
                        raise RuntimeError("Notification subscription ended")
                    window = response[state.index:state.index + NOTIFICATION_WINDOW]
                    state.notification_ack.clear()
                    state.notification_expected_ack = state.index + len(window) - 1
                    for packet in window:
                        if state.closed or not self.notifier.notifying:
                            raise RuntimeError("Notification session ended")
                        state.index += 1
                        self.notifier.send(packet)
                        # Bound the burst and yield to D-Bus/ATT.
                        await asyncio.sleep(0.004)
                    await asyncio.wait_for(state.notification_ack.wait(), timeout=NOTIFICATION_ACK_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            LOG.warning("Notification transfer interrupted (%s); reconnect to check request outcome", type(error).__name__)
            # Keep the session busy until a fresh INFO handshake replaces it.
        finally:
            if state.notification_task is asyncio.current_task():
                state.notification_task = None


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


class NotificationCharacteristic(Characteristic):
    def __init__(self, gateway):
        super().__init__(NOTIFY_UUID, ["notify"], gateway, "notify")
        self.value = b""
        self.notifying = False
        gateway.notifier = self

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> 'ay':
        return self.value

    @dbus_property(access=PropertyAccess.READ)
    def Notifying(self) -> 'b':
        return self.notifying

    @method()
    def StartNotify(self):
        if not self.notifying:
            self.notifying = True
            self.emit_properties_changed({"Notifying": True})
            LOG.info("Bluetooth push enabled")

    @method()
    def StopNotify(self):
        self.notifying = False
        self.emit_properties_changed({"Notifying": False})
        LOG.info("Bluetooth push disabled")
        for state in self.gateway.sessions.values():
            if state.notification_task:
                state.notification_task.cancel()

    def send(self, packet):
        if not self.notifying:
            raise RuntimeError("Not subscribed")
        self.value = bytes(packet)
        self.emit_properties_changed({"Value": self.value})

    def props(self):
        return {**super().props(), "Value": Variant("ay", self.value), "Notifying": Variant("b", self.notifying)}


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
    clear_ready(key_path.parent)
    key = load_key(key_path)
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    gateway = Gateway(key, GalaxyProxy(args.galaxy_port), key_path)
    objects = {
        SERVICE_PATH: GattService(),
        SERVICE_PATH + "/rx": Characteristic(RX_UUID, ["write"], gateway, "rx"),
        SERVICE_PATH + "/tx": Characteristic(TX_UUID, ["read"], gateway, "tx"),
        SERVICE_PATH + "/info": Characteristic(INFO_UUID, ["read"], gateway, "info"),
        SERVICE_PATH + "/notify": NotificationCharacteristic(gateway),
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
    watcher = asyncio.create_task(gateway.watch_key())
    try:
        await advertising.call_register_advertisement(ad_path, {})
        write_ready(key_path.parent)
        LOG.info("Galaxy BLE bridge ready on %s; forwarding to localhost:%s", adapter_path, args.galaxy_port)
        stopped = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stopped.set)
        await stopped.wait()
    finally:
        clear_ready(key_path.parent)
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
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
