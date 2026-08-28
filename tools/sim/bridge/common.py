import signal
import threading
import functools
import numpy as np

from collections import namedtuple
from enum import Enum
from multiprocessing import Process, Queue, Value
from abc import ABC, abstractmethod

from opendbc.car.honda.values import CruiseButtons
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper
from openpilot.selfdrive.test.helpers import set_params_enabled
from openpilot.tools.sim.lib.common import SimulatorState, World
from openpilot.tools.sim.lib.simulated_car import SimulatedCar
from openpilot.tools.sim.lib.simulated_sensors import SimulatedSensors

QueueMessage = namedtuple("QueueMessage", ["type", "info"], defaults=[None])

class QueueMessageType(Enum):
  START_STATUS = 0
  CONTROL_COMMAND = 1
  TERMINATION_INFO = 2
  CLOSE_STATUS = 3

def control_cmd_gen(cmd: str):
  return QueueMessage(QueueMessageType.CONTROL_COMMAND, cmd)

def rk_loop(function, hz, exit_event: threading.Event):
  rk = Ratekeeper(hz, None)
  while not exit_event.is_set():
    function()
    rk.keep_time()


class SimulatorBridge(ABC):
  TICKS_PER_FRAME = 5

  def __init__(self, dual_camera, high_quality):
    set_params_enabled()
    self.params = Params()
    self.params.put_bool("AlphaLongitudinalEnabled", True)

    self.rk = Ratekeeper(100, None)

    self.dual_camera = dual_camera
    self.high_quality = high_quality

    self._exit_event: threading.Event | None = None
    self._threads = []
    self._keep_alive = True
    self.started = Value('i', False)
    signal.signal(signal.SIGTERM, self._on_shutdown)
    self.simulator_state = SimulatorState()

    self.world: World | None = None

    self.past_startup_engaged = False
    self.startup_button_prev = True
    self.startup_set_count = 0
    self.auto_engage_speed_done = False
    self.AUTO_CRUISE_KPH = 60.0

    self.manual_throttle = 0.0
    self.manual_brake = 0.0
    self.manual_steer = 0.0

    self.test_run = False

  def _on_shutdown(self, signal, frame):
    self.shutdown()

  def shutdown(self):
    self._keep_alive = False

  def bridge_keep_alive(self, q: Queue, retries: int):
    try:
      self._run(q)
    finally:
      self.close("bridge terminated")

  def close(self, reason):
    self.started.value = False

    if self._exit_event is not None:
      self._exit_event.set()

    if self.world is not None:
      self.world.close(reason)

  def run(self, queue, retries=-1):
    bridge_p = Process(name="bridge", target=self.bridge_keep_alive, args=(queue, retries))
    bridge_p.start()
    return bridge_p

  def print_status(self):
    print(
    f"""
State:
Ignition: {self.simulator_state.ignition} Engaged: {self.simulator_state.is_engaged}
    """)

  @abstractmethod
  def spawn_world(self, q: Queue) -> World:
    pass

  def _run(self, q: Queue):
    self.world = self.spawn_world(q)

    self.simulated_car = SimulatedCar()
    self.simulated_sensors = SimulatedSensors(self.dual_camera)

    self._exit_event = threading.Event()

    self.simulated_car_thread = threading.Thread(target=rk_loop, args=(functools.partial(self.simulated_car.update, self.simulator_state),
                                                                        100, self._exit_event))
    self.simulated_car_thread.start()

    self.simulated_camera_thread = threading.Thread(target=rk_loop, args=(functools.partial(self.simulated_sensors.send_camera_images, self.world),
                                                                        20, self._exit_event))
    self.simulated_camera_thread.start()

    # Simulation tends to be slow in the initial steps. This prevents lagging later
    for _ in range(20):
      self.world.tick()

    while self._keep_alive:
      throttle_out = steer_out = brake_out = 0.0
      throttle_op = steer_op = brake_op = 0.0

      self.simulator_state.cruise_button = 0
      self.simulator_state.left_blinker = False
      self.simulator_state.right_blinker = False

      throttle_manual = self.manual_throttle
      steer_manual = self.manual_steer
      brake_manual = self.manual_brake

      # Read manual controls
      if not q.empty():
        message = q.get()
        if message.type == QueueMessageType.CONTROL_COMMAND:
          m = message.info.split('_')
          if m[0] == "steer":
            steer_manual = self.manual_steer = float(m[1])
          elif m[0] == "throttle":
            throttle_manual = self.manual_throttle = float(m[1])
          elif m[0] == "brake":
            brake_manual = self.manual_brake = float(m[1])
          elif m[0] == "cruise":
            if m[1] == "down":
              self.simulator_state.cruise_button = CruiseButtons.DECEL_SET
            elif m[1] == "up":
              self.simulator_state.cruise_button = CruiseButtons.RES_ACCEL
            elif m[1] == "cancel":
              self.simulator_state.cruise_button = CruiseButtons.CANCEL
              self.manual_throttle = self.manual_brake = self.manual_steer = 0.0
            elif m[1] == "main":
              self.simulator_state.cruise_button = CruiseButtons.MAIN
          elif m[0] == "blinker":
            if m[1] == "left":
              self.simulator_state.left_blinker = True
            elif m[1] == "right":
              self.simulator_state.right_blinker = True
          elif m[0] == "ignition":
            self.simulator_state.ignition = not self.simulator_state.ignition
          elif m[0] == "reset":
            self.world.reset()
          elif m[0] == "quit":
            break

      self.simulator_state.user_brake = brake_manual
      self.simulator_state.user_gas = throttle_manual
      self.simulator_state.user_torque = steer_manual * -10000

      steer_manual = steer_manual * -40

      # Update openpilot on current sensor state
      self.simulated_sensors.update(self.simulator_state, self.world)

      self.simulated_car.sm.update(0)
      self.simulator_state.is_engaged = self.simulated_car.sm['selfdriveState'].active

      if self.simulator_state.is_engaged:
        self.manual_throttle = self.manual_brake = self.manual_steer = 0.0
        throttle_op = np.clip(self.simulated_car.sm['carControl'].actuators.accel / 1.6, 0.0, 1.0)
        brake_op = np.clip(-self.simulated_car.sm['carControl'].actuators.accel / 4.0, 0.0, 1.0)
        steer_op = self.simulated_car.sm['carControl'].actuators.steeringAngleDeg

        # After auto-engaging at standstill the set speed is captured at ~floor
        # (a crawl). Ramp it up to a real driving speed via cruise-accel presses.
        if not self.auto_engage_speed_done and self.rk.frame % 5 == 0:
          if self.simulated_car.sm['carState'].vCruise < self.AUTO_CRUISE_KPH:
            self.simulator_state.cruise_button = CruiseButtons.RES_ACCEL
          else:
            self.auto_engage_speed_done = True

        self.past_startup_engaged = True
      elif not self.past_startup_engaged and self.simulated_car.sm['selfdriveState'].engageable:
        # Auto-engage whenever the car is ready. Cruise-Set (DECEL_SET) engages from
        # standstill; pressing periodically (not every frame) avoids ratcheting the set
        # speed down while still catching the moment the car becomes engageable.
        if self.rk.frame % 10 == 0:
          self.simulator_state.cruise_button = CruiseButtons.DECEL_SET

      throttle_out = throttle_op if self.simulator_state.is_engaged else throttle_manual
      brake_out = brake_op if self.simulator_state.is_engaged else brake_manual
      steer_out = steer_op if self.simulator_state.is_engaged else steer_manual

      self.world.apply_controls(steer_out, throttle_out, brake_out)
      self.world.read_state()
      self.world.read_sensors(self.simulator_state)

      if self.rk.frame % 300 == 0:
        try:
          from PIL import Image
          cam = getattr(self.world, 'road_image', None)
          if cam is not None and getattr(cam, 'any', None) and cam.any():
            Image.fromarray(cam[:, :, ::-1]).save(f"/tmp/kilo/cam_{self.rk.frame}.jpg", quality=90)
        except Exception as e:
          print(f"CAM-ERR {e}", flush=True)

      if self.rk.frame % 25 == 0 and not self.test_run:
        try:
          st = self.simulator_state
          eng = st.is_engaged
          engable = self.simulated_car.sm['selfdriveState'].engageable
          active = self.simulated_car.sm['selfdriveState'].active
          accel = self.simulated_car.sm['carControl'].actuators.accel if eng else float('nan')
          cs = self.simulated_car.sm['carState']
          sp = self.simulated_car.sm['starpilotPlan']
          rd = self.simulated_car.sm['radarState']
          m = self.simulated_car.sm['modelV2']
          lead = rd.leadOne
          print(f"BRIDGE engaged={eng} engable={engable} active={active} accel={accel:.2f} "
                f"gas={throttle_out:.2f} brake={brake_out:.2f} steer={steer_out:.1f} "
                f"v={st.speed if st.velocity is not None else -1:.2f} "
                f"pos=({st.position[0]:.1f},{st.position[1]:.1f}) yaw={st.bearing:.1f} vCruiseK={cs.vCruise:.0f} "
                f"forcStop={sp.forcingStop} apprStop={sp.approachStopLength:.1f} "
                f"modelLen={m.position.x[-1]:.0f} mVel={m.velocity.x[-1]:.1f} "
                f"mAcc={m.acceleration.x[-1]:.2f} sign={sp.stopSignConfirmed} "
                f"leadD={lead.dRel:.1f} leadV={lead.vLead:.1f}", flush=True)
        except Exception as e:
          import traceback; traceback.print_exc()
          print(f"BRIDGE-ERR {type(e).__name__}: {e}", flush=True)



      if self.world.exit_event.is_set():
        self.shutdown()

      if self.rk.frame % self.TICKS_PER_FRAME == 0:
        self.world.tick()
        self.world.read_cameras()

      # don't print during test, so no print/IO Block between OP and metadrive processes
      if not self.test_run and self.rk.frame % 25 == 0:
        self.print_status()

      self.started.value = True

      self.rk.keep_time()
