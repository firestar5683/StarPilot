"""Optional G90 display input; missing radar never gates ordinary controls."""
from opendbc.car.hyundai.g90_lead import LeadObservation
from openpilot.starpilot.longitudinal.radar_lead_context import RadarLeadContext


class G90LeadInputs(RadarLeadContext):
  def __init__(self):
    super().__init__(require_radar=True)

  def update(self):
    context = super().update()
    if context is None:
      return None
    radar = context.radar
    return LeadObservation(context.drive_id, radar.producer_ns, radar.receipt_ns, context.mono_now_ns,
                           radar.present, radar.distance, radar.relative_speed)
