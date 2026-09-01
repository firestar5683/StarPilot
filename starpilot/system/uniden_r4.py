import json
import os
import subprocess
import time
from openpilot.starpilot.system.uniden_shm import set_shm_param, get_shm_param

PARAMS_PATH = '/data/params/d'

DEFAULTS = {
    "UnidenR4Enabled": True,
    "UnidenR4Mac": "",                  # Dynamically discovered or configured
    "UnidenR4Mode": "all_threat",       # all_threat, highway, city, advanced
    "UnidenR4AutoMute": True,
    "UnidenR4QuietRideSpeed": 35,       # mph
    "UnidenR4Volume": 5,                # 0-8
    "UnidenR4Brightness": "auto",       # auto, bright, dim, dimmer, dark, brightest, off
    "UnidenR4KBand": True,
    "UnidenR4KaBand": True,
    "UnidenR4Laser": True,
    "UnidenR4MRCD": True,
    "UnidenR4POP": False,
    "UnidenR4MuteMemory": True,
    "UnidenR4AlertVolume": 5,
    "UnidenAutoSlowdown": True,
    "UnidenAutoSlowdownBands": "KA,K,LASER,MRCD,POP",
}

# Mapping for Uniden R-series BLE command protocol (SETC IDs verified via Android R/TACH trace)
BRIGHTNESS_CMDS = {
    "auto": "BTreqSETC:102=0",
    "dark": "BTreqSETC:102=1",
    "dimmer": "BTreqSETC:102=2",
    "dim": "BTreqSETC:102=3",
    "bright": "BTreqSETC:102=4",
    "brightest": "BTreqSETC:102=5",
    "off": "BTreqSETC:102=6",
}

MODE_CMDS = {
    "all_threat": "BTreqSETC:100=1",
    "highway": "BTreqSETC:100=2",
    "city": "BTreqSETC:100=3",
    "advanced": "BTreqSETC:100=4",
}

def get_param(name, default):
    p = os.path.join(PARAMS_PATH, name)
    if os.path.exists(p):
        try:
            with open(p, 'r') as f:
                val = f.read().strip()
                if isinstance(default, bool):
                    return val == '1' or val.lower() == 'true'
                elif isinstance(default, int):
                    return int(val)
                return val
        except Exception:
            return default
    return default

def set_param(name, value):
    os.makedirs(PARAMS_PATH, exist_ok=True)
    p = os.path.join(PARAMS_PATH, name)
    try:
        with open(p, 'w') as f:
            if isinstance(value, bool):
                f.write('1' if value else '0')
            else:
                f.write(str(value))
        return True
    except Exception as e:
        print(f"Failed to write param {name}: {e}")
        return False

def discover_uniden_device():
    """Dynamically discover any paired or connected Uniden R-series detector (R4@*, R8@*, etc.)"""
    configured_mac = get_param("UnidenR4Mac", "")
    if configured_mac:
        return configured_mac

    try:
        out = subprocess.check_output(['bluetoothctl', 'devices'], stderr=subprocess.DEVNULL).decode()
        for line in out.splitlines():
            # Matches 'Device XX:XX:XX:XX:XX:XX R4@...' or 'R8@...' or 'Uniden...'
            if any(k in line.upper() for k in ["R4@", "R8@", "R9@", "UNIDEN"]):
                parts = line.split()
                if len(parts) >= 2:
                    mac = parts[1].strip()
                    set_param("UnidenR4Mac", mac)
                    return mac
    except Exception:
        pass
    return ""

def get_char_write_path(mac=None):
    """Dynamically resolve the BlueZ D-Bus object path for the detector's command characteristic."""
    if not mac:
        mac = discover_uniden_device()
    if not mac:
        return None
    dev_path = f"/org/bluez/hci0/dev_{mac.replace(':', '_')}"
    return f"{dev_path}/service0028/char0029"

def send_ble_command(cmd_str):
    """Send GATT command via dynamic D-Bus path."""
    char_write = get_char_write_path()
    if not char_write:
        return False
    try:
        byte_list = [str(b) for b in cmd_str.encode('utf-8')]
        count_str = str(len(byte_list))
        cmd = ['busctl', 'call', 'org.bluez', char_write, 'org.bluez.GattCharacteristic1', 'WriteValue', 'aya{sv}', count_str] + byte_list + ['0']
        subprocess.run(cmd, check=False, timeout=2)
        return True
    except Exception as e:
        print(f"BLE send error ({cmd_str}): {e}")
        return False

def get_all_settings():
    settings = {}
    for k, v in DEFAULTS.items():
        settings[k] = get_param(k, v)
    if not settings.get("UnidenR4Mac"):
        settings["UnidenR4Mac"] = discover_uniden_device()
    return settings

def update_settings(new_settings):
    for k, v in new_settings.items():
        if k in DEFAULTS:
            set_param(k, v)
            # Dispatch live BLE GATT commands directly to the Uniden R4
            if k == "UnidenR4Brightness":
                cmd = BRIGHTNESS_CMDS.get(str(v).lower())
                if cmd:
                    send_ble_command(cmd)
            elif k == "UnidenR4Volume":
                send_ble_command(f"BTreqSETC:101={v}")
            elif k == "UnidenR4Mode":
                cmd = MODE_CMDS.get(str(v).lower())
                if cmd:
                    send_ble_command(cmd)
            elif k == "UnidenR4AutoMute":
                send_ble_command(f"BTreqSETC:103={1 if v else 0}")
            elif k == "UnidenR4MuteMemory":
                send_ble_command(f"BTreqSETC:104={1 if v else 0}")
            elif k == "UnidenR4QuietRideSpeed":
                send_ble_command(f"BTreqSETC:105={v}")
            elif k == "UnidenR4KBand":
                send_ble_command(f"BTreqSETC:110={1 if v else 0}")
            elif k == "UnidenR4KaBand":
                send_ble_command(f"BTreqSETC:111={1 if v else 0}")
            elif k == "UnidenR4Laser":
                send_ble_command(f"BTreqSETC:112={1 if v else 0}")
            elif k == "UnidenR4MRCD":
                send_ble_command(f"BTreqSETC:113={1 if v else 0}")
            elif k == "UnidenR4POP":
                send_ble_command(f"BTreqSETC:114={1 if v else 0}")
            elif k == "UnidenR4AlertVolume":
                send_ble_command(f"BTreqSETC:115={v}")
    return get_all_settings()

def get_connection_status():
    mac = discover_uniden_device()
    is_connected_shm = get_shm_param("UnidenRadarConnected", False)
    status = {
        "mac": mac,
        "name": "Uniden Radar Detector",
        "connected": bool(is_connected_shm),
        "trusted": False,
        "rssi": None,
    }
    if not mac:
        return status

    try:
        out = subprocess.check_output(['bluetoothctl', 'info', mac], stderr=subprocess.DEVNULL, timeout=1).decode()
        if not status["connected"]:
            status["connected"] = "Connected: yes" in out
        status["trusted"] = "Trusted: yes" in out
        for line in out.splitlines():
            if "Name:" in line:
                status["name"] = line.split("Name:")[1].strip()
            if "RSSI:" in line:
                try:
                    status["rssi"] = int(line.split("(")[1].split(")")[0])
                except Exception:
                    pass
    except Exception:
        pass
    return status

def trigger_action(action):
    if action == "connect":
        # Signal the background daemon to initiate connection immediately (even offroad)
        set_shm_param("UnidenManualConnectTrigger", True)
        mac = discover_uniden_device()
        if mac:
            try:
                subprocess.run(['bluetoothctl', 'connect', mac], check=False, timeout=5)
            except Exception:
                pass
            return {"status": "ok", "message": f"Connecting to {mac}..."}
        return {"status": "ok", "message": "Scanning and connecting to nearby Uniden detector..."}
        
    elif action == "disconnect":
        mac = discover_uniden_device()
        if mac:
            try:
                subprocess.run(['bluetoothctl', 'disconnect', mac], check=False, timeout=5)
                return {"status": "ok", "message": f"Disconnected from {mac}."}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "ok", "message": "Disconnected."}
        
    elif action == "mute":
        try:
            send_ble_command("BTreqMUTE:1")
            return {"status": "ok", "message": "Mute command sent."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    return {"status": "error", "message": "Unknown action"}
