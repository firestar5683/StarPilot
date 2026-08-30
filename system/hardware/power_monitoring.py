import time
import threading

from types import SimpleNamespace

from openpilot.common.params import Params
from openpilot.system.hardware import HARDWARE
from openpilot.common.swaglog import cloudlog
from openpilot.system.statsd import statlog

CAR_VOLTAGE_LOW_PASS_K = 0.011 # LPF gain for 45s tau (dt/tau / (dt/tau + 1))

# While driving, a battery charges completely in about 30-60 minutes
CAR_BATTERY_CAPACITY_uWh = 30e6
CAR_CHARGING_RATE_W = 45

VBATT_PAUSE_CHARGING = 11.8           # Lower limit on the LPF car battery voltage
MAX_TIME_OFFROAD_S = 30*3600
MIN_ON_TIME_S = 3600
DELAY_SHUTDOWN_TIME_S = 300 # Wait at least DELAY_SHUTDOWN_TIME_S seconds after offroad_time to shutdown.
VOLTAGE_SHUTDOWN_MIN_OFFROAD_TIME_S = 60
VOLTAGE_SHUTDOWN_SUSTAINED_TIME_S = 300.0

class PowerMonitoring:
  def __init__(self):
    self.params = Params()
    self.last_measurement_time = None           # Used for integration delta
    self.last_save_time = 0                     # Used for saving current value in a param
    self.power_used_uWh = 0                     # Integrated power usage in uWh since going into offroad
    self.next_pulsed_measurement_time = None
    self.car_voltage_mV = 12e3                  # Low-passed version of peripheralState voltage
    self.car_voltage_instant_mV = 12e3          # Last value of peripheralState voltage
    self.low_voltage_start_time = None          # Monotonic timestamp when low voltage was first observed
    self.integration_lock = threading.Lock()

    # Preserve an exhausted persisted value so the shutdown policy can act on it.
    # A missing or malformed value is treated as a newly initialized battery.
    car_battery_capacity_uWh = self.params.get_int("CarBatteryCapacity", default=CAR_BATTERY_CAPACITY_uWh)
    if car_battery_capacity_uWh < 0:
      car_battery_capacity_uWh = CAR_BATTERY_CAPACITY_uWh

    # Reset low but non-zero estimates; zero means the estimate is exhausted.
    self.car_battery_capacity_uWh = (
      0 if car_battery_capacity_uWh == 0 else max((CAR_BATTERY_CAPACITY_uWh / 2), car_battery_capacity_uWh)
    )

  # Calculation tick
  def calculate(self, voltage: int | None, ignition: bool):
    try:
      now = time.monotonic()

      # If peripheralState is None, we're probably not in a car, so we don't care
      if voltage is None:
        with self.integration_lock:
          self.last_measurement_time = None
          self.next_pulsed_measurement_time = None
          self.power_used_uWh = 0
        return

      # Low-pass battery voltage
      self.car_voltage_instant_mV = voltage
      self.car_voltage_mV = ((voltage * CAR_VOLTAGE_LOW_PASS_K) + (self.car_voltage_mV * (1 - CAR_VOLTAGE_LOW_PASS_K)))
      statlog.gauge("car_voltage", self.car_voltage_mV / 1e3)

      # Cap the car battery power and save it in a param every 10-ish seconds
      self.car_battery_capacity_uWh = max(self.car_battery_capacity_uWh, 0)
      self.car_battery_capacity_uWh = min(self.car_battery_capacity_uWh, CAR_BATTERY_CAPACITY_uWh)
      if now - self.last_save_time >= 10:
        self.params.put_nonblocking("CarBatteryCapacity", int(self.car_battery_capacity_uWh))
        self.last_save_time = now

      # First measurement, set integration time
      with self.integration_lock:
        if self.last_measurement_time is None:
          self.last_measurement_time = now
          return

      if ignition:
        # If there is ignition, we integrate the charging rate of the car
        with self.integration_lock:
          self.power_used_uWh = 0
          integration_time_h = (now - self.last_measurement_time) / 3600
          if integration_time_h < 0:
            raise ValueError(f"Negative integration time: {integration_time_h}h")
          self.car_battery_capacity_uWh += (CAR_CHARGING_RATE_W * 1e6 * integration_time_h)
          self.last_measurement_time = now
      else:
        # Get current power draw somehow
        current_power = HARDWARE.get_current_power_draw()

        # Do the integration
        self._perform_integration(now, current_power)
    except Exception:
      cloudlog.exception("Power monitoring calculation failed")

  def _perform_integration(self, t: float, current_power: float) -> None:
    with self.integration_lock:
      try:
        if self.last_measurement_time:
          integration_time_h = (t - self.last_measurement_time) / 3600
          power_used = (current_power * 1000000) * integration_time_h
          if power_used < 0:
            raise ValueError(f"Negative power used! Integration time: {integration_time_h} h Current Power: {power_used} uWh")
          self.power_used_uWh += power_used
          self.car_battery_capacity_uWh -= power_used
          self.last_measurement_time = t
      except Exception:
        cloudlog.exception("Integration failed")

  # Get the power usage
  def get_power_used(self) -> int:
    return int(self.power_used_uWh)

  def get_car_battery_capacity(self) -> int:
    return int(self.car_battery_capacity_uWh)

  # See if we need to shutdown
  def shutdown_reason(self, ignition: bool, in_car: bool, offroad_timestamp: float | None,
                      started_seen: bool, starpilot_toggles: SimpleNamespace) -> str | None:
    if offroad_timestamp is None:
      self.low_voltage_start_time = None
      return None

    now = time.monotonic()
    offroad_time = (now - offroad_timestamp)

    cutoff_voltage = starpilot_toggles.low_voltage_shutdown if getattr(starpilot_toggles, "low_voltage_shutdown", 0) > 0 else 11.8
    is_below_voltage = self.car_voltage_mV < (cutoff_voltage * 1e3)

    if is_below_voltage and offroad_time > VOLTAGE_SHUTDOWN_MIN_OFFROAD_TIME_S:
      if self.low_voltage_start_time is None:
        self.low_voltage_start_time = now
      low_voltage_sustained_time = now - self.low_voltage_start_time
      low_voltage_shutdown = low_voltage_sustained_time >= VOLTAGE_SHUTDOWN_SUSTAINED_TIME_S
    else:
      self.low_voltage_start_time = None
      low_voltage_shutdown = False

    reason = None
    if starpilot_toggles.device_shutdown_time > 0 and offroad_time > starpilot_toggles.device_shutdown_time:
      reason = "offroad_timeout"
    elif low_voltage_shutdown:
      reason = "low_voltage"
    elif self.car_battery_capacity_uWh <= 0:
      reason = "battery_capacity_exhausted"

    should_shutdown = reason is not None
    should_shutdown &= not ignition
    should_shutdown &= (not self.params.get_bool("DisablePowerDown"))
    should_shutdown &= in_car
    should_shutdown &= offroad_time > DELAY_SHUTDOWN_TIME_S

    forced = self.params.get_bool("ForcePowerDown")
    should_shutdown |= forced
    should_shutdown &= started_seen or (now > MIN_ON_TIME_S)
    if not should_shutdown:
      return None
    return "forced_power_down" if forced else reason

  def should_shutdown(self, ignition: bool, in_car: bool, offroad_timestamp: float | None,
                      started_seen: bool, starpilot_toggles: SimpleNamespace):
    return self.shutdown_reason(ignition, in_car, offroad_timestamp, started_seen, starpilot_toggles) is not None
