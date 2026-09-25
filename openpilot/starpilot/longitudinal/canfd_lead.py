"""Optional current-drive CANFD radar/camera lead inputs in one clock domain."""
from opendbc.car.hyundai.canfd_lead import ABSENT, CANFDLeadObservation, select_lead
from openpilot.starpilot.longitudinal.radar_lead_context import RadarLeadContext


class CANFDLeadInputs:
  def __init__(self):
    self.context = RadarLeadContext(require_radar=False)

  def update(self, camera, hud_visible, control_mono_ns):
    context = self.context.update()
    if context is None or type(control_mono_ns) is not int or not 0 <= context.mono_now_ns-control_mono_ns <= 150_000_000:
      return ABSENT
    radar = context.radar
    radar_observation = None if radar is None else CANFDLeadObservation(
      radar.present, radar.distance, radar.relative_speed, radar.producer_ns+context.offset_ns)
    camera_value = camera.current(context.boot_now_ns, context.boot_floor_ns) if camera is not None else None
    camera_observation = None if camera_value is None else CANFDLeadObservation(
      camera_value.visible, camera_value.distance_m, camera_value.relative_speed_mps, camera_value.producer_boot_ns)
    return select_lead(radar_observation, camera_observation, hud_visible=hud_visible,
                       observed_ns=context.boot_now_ns, epoch_floor_ns=context.boot_floor_ns)
