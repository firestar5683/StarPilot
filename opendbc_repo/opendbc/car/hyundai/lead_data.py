from dataclasses import dataclass


@dataclass(frozen=True)
class CanLeadData:
  object_gap: int = 0
  lead_distance: float = 0.0
  lead_rel_speed: float = 0.0
  lead_visible: bool = False

  @property
  def object_rel_gap(self) -> int:
    return 0 if self.lead_distance == 0 else 2 if self.lead_rel_speed < -0.2 else 1


def _hysteresis_update(current, new_value, counter, threshold):
  if new_value == current:
    return current, 0

  counter += 1
  return (new_value, 0) if counter >= threshold else (current, counter)


class CanLeadDataState:
  LEAD_HYSTERESIS_FRAMES = 50

  def __init__(self):
    self._lead_on_counter = 0
    self._lead_off_counter = 0
    self._gap_counter = 0
    self._lead_visible = False
    self._object_gap = 0

  @staticmethod
  def _get_object_gap(lead_distance: float) -> int:
    if lead_distance == 0:
      return 0
    if lead_distance < 20:
      return 2
    if lead_distance < 25:
      return 3
    if lead_distance < 30:
      return 4
    return 5

  def update(self, lead_distance: float, lead_rel_speed: float, lead_visible: bool) -> CanLeadData:
    counter = self._lead_on_counter if lead_visible else self._lead_off_counter
    self._lead_visible, counter = _hysteresis_update(
      self._lead_visible, lead_visible, counter, self.LEAD_HYSTERESIS_FRAMES,
    )
    if lead_visible:
      self._lead_on_counter = counter
      self._lead_off_counter = 0
    else:
      self._lead_off_counter = counter
      self._lead_on_counter = 0

    object_gap = self._get_object_gap(lead_distance)
    self._object_gap, self._gap_counter = _hysteresis_update(
      self._object_gap, object_gap, self._gap_counter, self.LEAD_HYSTERESIS_FRAMES,
    )

    return CanLeadData(self._object_gap, lead_distance, lead_rel_speed, self._lead_visible)
