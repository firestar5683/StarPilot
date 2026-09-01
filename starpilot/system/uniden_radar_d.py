#!/usr/bin/env python3
import asyncio
import os
import time
import bleak
from openpilot.common.params import Params
from starpilot.system.uniden_r4 import discover_uniden_device, DEFAULTS, get_param, set_param
from r8link.protocol import parse_alerts, parse_telemetry

SHM_PARAMS_PATH = "/dev/shm/params/d"

def set_shm_param(name, value):
    try:
        os.makedirs(SHM_PARAMS_PATH, exist_ok=True)
        p = os.path.join(SHM_PARAMS_PATH, name)
        with open(p, "w") as f:
            if isinstance(value, bool):
                f.write("1" if value else "0")
            else:
                f.write(str(value))
        return True
    except Exception:
        return False

def get_shm_param(name, default):
    p = os.path.join(SHM_PARAMS_PATH, name)
    if os.path.exists(p):
        try:
            with open(p, "r") as f:
                val = f.read().strip()
                if isinstance(default, bool):
                    return val == "1" or val.lower() == "true"
                elif isinstance(default, int):
                    return int(val)
                elif isinstance(default, float):
                    return float(val)
                return val
        except Exception:
            return default
    return default

ALERT_UUID = "6eb675ab-8bd1-1b9a-7444-621e52ec6823"
TEL_UUID   = "6c290d2e-1c03-aca1-ab48-a9b908bae79e"
RESP_UUID  = "5987b4ef-3bfa-76a8-e642-92933c31434f"
SET1_UUID  = "2d86686a-53dc-25b3-0c4a-f0e10c8dee20"
WRITE_UUID = "2c86686a-53dc-25b3-0c4a-f0e10c8dee20"

# Maximum time (seconds) to attempt connecting when first going onroad
ONROAD_CONNECT_WINDOW_SEC = 180.0  # 3 minutes

def clear_active_alert():
    set_shm_param("UnidenRadarAlertActive", False)
    set_shm_param("UnidenRadarAlertBand", "")
    set_shm_param("UnidenRadarAlertStrength", 0)
    set_shm_param("UnidenRadarAlertDescription", "")

async def run_uniden_daemon():
    print("[uniden_radar_d] Starting Uniden Radar Detector background monitor...")
    clear_active_alert()
    set_shm_param("UnidenRadarConnected", False)
    
    params = Params()
    last_alert_time = 0.0
    was_onroad = False
    onroad_start_time = 0.0

    while True:
        try:
            enabled = get_param("UnidenR4Enabled", True)
            if not enabled:
                clear_active_alert()
                set_shm_param("UnidenRadarConnected", False)
                await asyncio.sleep(5.0)
                continue

            # Check if user manually clicked "Connect" / "Pair" in Galaxy UI (works even when offroad)
            manual_connect = get_shm_param("UnidenManualConnectTrigger", False)
            if manual_connect:
                set_shm_param("UnidenManualConnectTrigger", False)
                manual_window_start = time.monotonic()
                print("[uniden_radar_d] Manual connection requested by user (Galaxy UI)!")
            else:
                manual_window_start = 0.0

            # Check car onroad / driving state
            is_onroad = bool(params.get_bool("IsOnroad"))
            
            # Detect transition to onroad
            if is_onroad and not was_onroad:
                onroad_start_time = time.monotonic()
                print("[uniden_radar_d] Car transitioned ONROAD! Starting 3-minute connection window...")
            elif not is_onroad:
                onroad_start_time = 0.0

            was_onroad = is_onroad

            # Determine if we should attempt connection right now:
            # 1. Manual user trigger in UI (active for 60 seconds after button press)
            # 2. Onroad initial 3-minute connection window
            is_manual_active = manual_window_start > 0 and (time.monotonic() - manual_window_start < 60.0)
            is_onroad_window_active = is_onroad and (time.monotonic() - onroad_start_time <= ONROAD_CONNECT_WINDOW_SEC)

            if not is_manual_active and not is_onroad_window_active:
                # Offroad (without manual trigger) or past 3-minute onroad window: sleep quietly
                clear_active_alert()
                set_shm_param("UnidenRadarConnected", False)
                await asyncio.sleep(2.0)
                continue

            mac = discover_uniden_device()
            if not mac:
                # If no detector paired yet, try a quick scan
                clear_active_alert()
                await asyncio.sleep(4.0)
                continue

            print(f"[uniden_radar_d] Attempting connection to {mac}...")
            client = bleak.BleakClient(mac, timeout=12.0)
            await client.connect()
            print(f"[uniden_radar_d] Connected to {mac}!")
            set_shm_param("UnidenRadarConnected", True)

            def on_alert_received(sender, data):
                nonlocal last_alert_time
                try:
                    alerts = parse_alerts(data)
                    slowdown_enabled = get_param("UnidenAutoSlowdown", True)
                    slowdown_bands_str = get_param("UnidenAutoSlowdownBands", "KA,K,LASER,MRCD,POP")
                    allowed_bands = [b.strip().upper() for b in slowdown_bands_str.split(",") if b.strip()]

                    # Check for active, relevant radar threats
                    threats = [a for a in alerts if a.band.upper() in allowed_bands and (a.strength or 0) > 0]
                    if threats:
                        # Pick highest threat / primary alert
                        primary = max(threats, key=lambda a: a.strength or 0)
                        last_alert_time = time.monotonic()
                        set_shm_param("UnidenRadarAlertActive", True)
                        set_shm_param("UnidenRadarAlertBand", primary.band)
                        set_shm_param("UnidenRadarAlertStrength", primary.strength or 0)
                        set_shm_param("UnidenRadarAlertDescription", primary.description or primary.band)
                    else:
                        # Decay active alert state after 1.5 seconds of clean air
                        if time.monotonic() - last_alert_time > 1.5:
                            clear_active_alert()
                except Exception as e:
                    print(f"[uniden_radar_d] Error parsing alert packet: {e}")

            def on_telemetry_received(sender, data):
                try:
                    tel = parse_telemetry(data)
                    if tel.voltage is not None:
                        set_shm_param("UnidenRadarVoltage", float(tel.voltage))
                except Exception:
                    pass

            # Register notifications
            try:
                await client.start_notify(ALERT_UUID, on_alert_received)
                await client.start_notify(TEL_UUID, on_telemetry_received)
                await client.start_notify(RESP_UUID, lambda s, d: None)
                await client.start_notify(SET1_UUID, lambda s, d: None)
            except Exception as e:
                print(f"[uniden_radar_d] Notify registration warning: {e}")

            # Send init handshake
            try:
                await client.write_gatt_char(WRITE_UUID, b"BTreqGURL:", response=False)
                await asyncio.sleep(0.3)
                await client.write_gatt_char(WRITE_UUID, b"BTreqGWAP:", response=False)
            except Exception:
                pass

            # Monitor loop while connected
            while client.is_connected:
                # Clear alert state if no alerts received recently
                if time.monotonic() - last_alert_time > 2.0:
                    clear_active_alert()
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[uniden_radar_d] Connection dropped or error: {e}")
        finally:
            clear_active_alert()
            set_shm_param("UnidenRadarConnected", False)
            await asyncio.sleep(3.0)

def main():
    asyncio.run(run_uniden_daemon())

if __name__ == "__main__":
    main()
