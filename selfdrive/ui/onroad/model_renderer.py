import colorsys
import numpy as np
import pyray as rl
from cereal import messaging, car
from dataclasses import dataclass, field
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.params import Params
from openpilot.common.constants import CV
from openpilot.selfdrive.locationd.calibrationd import HEIGHT_INIT
from openpilot.selfdrive.ui.lib.starpilot_theme import get_param_color, get_theme_color, get_visual_color, is_stock_color_scheme, with_alpha
from openpilot.selfdrive.ui.lib.starpilot_visuals import lead_indicator_enabled
from openpilot.selfdrive.ui.ui_state import ui_state, UIStatus
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.shader_polygon import draw_polygon, Gradient
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget

CLIP_MARGIN = 500
MIN_DRAW_DISTANCE = 10.0
MAX_DRAW_DISTANCE = 100.0
RAINBOW_GRADIENT_COLOR_COUNT = 19
RAINBOW_SCROLL_SPEED_DEG_PER_SEC = 60.0
STOCK_LANE_LINES_COLOR = rl.Color(255, 255, 255, 255)
DEFAULT_LANE_LINES_WIDTH = 4.0
DEFAULT_PATH_EDGE_WIDTH = 20.0
DEFAULT_PATH_WIDTH = 6.1
DEFAULT_ROAD_EDGES_WIDTH = 2.0

THROTTLE_COLORS = [
  rl.Color(13, 248, 122, 102),   # HSLF(148/360, 0.94, 0.51, 0.4)
  rl.Color(114, 255, 92, 89),    # HSLF(112/360, 1.0, 0.68, 0.35)
  rl.Color(114, 255, 92, 0),     # HSLF(112/360, 1.0, 0.68, 0.0)
]

NO_THROTTLE_COLORS = [
  rl.Color(242, 242, 242, 102), # HSLF(148/360, 0.0, 0.95, 0.4)
  rl.Color(242, 242, 242, 89),  # HSLF(112/360, 0.0, 0.95, 0.35)
  rl.Color(242, 242, 242, 0),   # HSLF(112/360, 0.0, 0.95, 0.0)
]

@dataclass
class ModelPoints:
  raw_points: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float32))
  projected_points: np.ndarray = field(default_factory=lambda: np.empty((0, 2), dtype=np.float32))


@dataclass
class LeadVehicle:
  glow: list[float] = field(default_factory=list)
  chevron: list[float] = field(default_factory=list)
  fill_alpha: int = 0


class ModelRenderer(Widget):
  def __init__(self):
    super().__init__()
    self._longitudinal_control = False
    self._experimental_mode = False
    self._blend_filter = FirstOrderFilter(1.0, 0.25, 1 / gui_app.target_fps)
    self._prev_allow_throttle = True
    self._lane_line_probs = np.zeros(4, dtype=np.float32)
    self._road_edge_stds = np.zeros(2, dtype=np.float32)
    self._lead_vehicles = [LeadVehicle(), LeadVehicle()]
    self._adjacent_lead_vehicles = [LeadVehicle(), LeadVehicle()]
    self._path_offset_z = HEIGHT_INIT[0]

    # Adjacent path vertices (left, right)
    self._adjacent_path_vertices = [np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32)]
    # Outer path polygon for edge rendering
    self._track_edge_vertices = np.empty((0, 2), dtype=np.float32)

    # Initialize ModelPoints objects
    self._path = ModelPoints()
    self._lane_lines = [ModelPoints() for _ in range(4)]
    self._road_edges = [ModelPoints() for _ in range(2)]
    self._acceleration_x = np.empty((0,), dtype=np.float32)

    # Transform matrix (3x3 for car space to screen space)
    self._car_space_transform = np.zeros((3, 3), dtype=np.float32)
    self._transform_dirty = True
    self._clip_region = None

    self._exp_gradient = Gradient(
      start=(0.0, 1.0),  # Bottom of path
      end=(0.0, 0.0),  # Top of path
      colors=[],
      stops=[],
    )

    # Get longitudinal control setting from car parameters
    self._params = Params()
    if car_params := self._params.get("CarParams"):
      cp = messaging.log_from_bytes(car_params, car.CarParams)
      self._longitudinal_control = cp.openpilotLongitudinalControl

  def set_transform(self, transform: np.ndarray):
    self._car_space_transform = transform.astype(np.float32)
    self._transform_dirty = True

  def _render(self, rect: rl.Rectangle):
    sm = ui_state.sm

    # Check if data is up-to-date
    if (sm.recv_frame["liveCalibration"] < ui_state.started_frame or
        sm.recv_frame["modelV2"] < ui_state.started_frame):
      return

    # Set up clipping region
    self._clip_region = rl.Rectangle(
      rect.x - CLIP_MARGIN, rect.y - CLIP_MARGIN, rect.width + 2 * CLIP_MARGIN, rect.height + 2 * CLIP_MARGIN
    )

    # Update state
    self._experimental_mode = sm['selfdriveState'].experimentalMode

    live_calib = sm['liveCalibration']
    self._path_offset_z = live_calib.height[0] if live_calib.height else HEIGHT_INIT[0]

    if sm.updated['carParams']:
      self._longitudinal_control = sm['carParams'].openpilotLongitudinalControl

    model = sm['modelV2']
    radar_state = sm['radarState'] if sm.valid['radarState'] else None
    lead_one = radar_state.leadOne if radar_state else None

    # StarPilot lead indicator visibility conditions
    hide_lead_marker = self._params.get_bool("HideLeadMarker")
    self._lead_info_enabled = self._params.get_bool("LeadInfo")
    self._use_rainbow = self._params.get_bool('RainbowPath', default=False)
    self._use_accel_path = self._params.get_bool('AccelerationPath', default=True)
    self._is_metric = self._params.get_bool('IsMetric')
    lead_info_enabled = self._lead_info_enabled
    render_lead_indicator = (self._longitudinal_control or lead_info_enabled) and radar_state is not None and not hide_lead_marker

    # Update model data when needed
    model_updated = sm.updated['modelV2']
    if model_updated or sm.updated['radarState'] or self._transform_dirty:
      if model_updated:
        self._update_raw_points(model)

      path_x_array = self._path.raw_points[:, 0]
      if path_x_array.size == 0:
        return

      self._update_model(lead_one, path_x_array)
      if render_lead_indicator:
        self._update_leads(radar_state, path_x_array)
        if sm.valid.get("starpilotRadarState", False):
          self._update_adjacent_leads(sm["starpilotRadarState"], path_x_array)
      self._transform_dirty = False

    self._lead_text_rects = []
    self._adjacent_lead_text_rects = []

    # Draw elements
    self._draw_lane_lines()
    self._draw_path(sm)

    if render_lead_indicator and radar_state:
      self._draw_lead_indicator(radar_state)
      # Adjacent leads may be published by radard for non-UI consumers (e.g. HumanLaneChanges),
      # so gate drawing on the AdjacentLeadsUI param directly.
      if sm.valid.get("starpilotRadarState", False) and self._params.get_bool("AdjacentLeadsUI"):
        self._draw_adjacent_leads()

    self._draw_radar_tracks()

  def _update_raw_points(self, model):
    """Update raw 3D points from model data"""
    self._path.raw_points = np.array([model.position.x, model.position.y, model.position.z], dtype=np.float32).T

    # Model outputs can vary by branch/model family; keep renderer bounded to
    # the fixed number of lane/edge slots used by the UI.
    for lane_line in self._lane_lines:
      lane_line.raw_points = np.empty((0, 3), dtype=np.float32)
    for i in range(min(len(self._lane_lines), len(model.laneLines))):
      lane_line = model.laneLines[i]
      self._lane_lines[i].raw_points = np.array([lane_line.x, lane_line.y, lane_line.z], dtype=np.float32).T

    for road_edge in self._road_edges:
      road_edge.raw_points = np.empty((0, 3), dtype=np.float32)
    for i in range(min(len(self._road_edges), len(model.roadEdges))):
      road_edge = model.roadEdges[i]
      self._road_edges[i].raw_points = np.array([road_edge.x, road_edge.y, road_edge.z], dtype=np.float32).T

    lane_line_probs = np.array(model.laneLineProbs, dtype=np.float32)
    self._lane_line_probs = np.zeros(len(self._lane_lines), dtype=np.float32)
    self._lane_line_probs[:min(len(self._lane_lines), len(lane_line_probs))] = lane_line_probs[:len(self._lane_lines)]

    road_edge_stds = np.array(model.roadEdgeStds, dtype=np.float32)
    self._road_edge_stds = np.ones(len(self._road_edges), dtype=np.float32)
    self._road_edge_stds[:min(len(self._road_edges), len(road_edge_stds))] = road_edge_stds[:len(self._road_edges)]
    self._acceleration_x = np.array(model.acceleration.x, dtype=np.float32)

  def _update_leads(self, radar_state, path_x_array):
    """Update positions of lead vehicles"""
    self._lead_vehicles = [LeadVehicle(), LeadVehicle()]
    leads = [radar_state.leadOne, radar_state.leadTwo]

    for i, lead_data in enumerate(leads):
      if lead_data and lead_data.status:
        d_rel, y_rel, v_rel = lead_data.dRel, lead_data.yRel, lead_data.vRel
        idx = self._get_path_length_idx(path_x_array, d_rel)

        # Get z-coordinate from path at the lead vehicle position
        z = self._path.raw_points[idx, 2] if idx < len(self._path.raw_points) else 0.0
        point = self._map_to_screen(d_rel, -y_rel, z + self._path_offset_z)
        if point:
          self._lead_vehicles[i] = self._update_lead_vehicle(d_rel, v_rel, point, self._rect)

  def _update_model(self, lead, path_x_array):
    """Update model visualization data based on model message"""
    model_ui_enabled = self._params.get_bool('ModelUI', default=True)
    custom_path_width, pw = self._param_float_changed('PathWidth', DEFAULT_PATH_WIDTH) if model_ui_enabled else (False, DEFAULT_PATH_WIDTH)
    custom_lane_line_width, llw = self._param_float_changed('LaneLinesWidth', DEFAULT_LANE_LINES_WIDTH) if model_ui_enabled else (False, DEFAULT_LANE_LINES_WIDTH)
    custom_road_edge_width, rew = self._param_float_changed('RoadEdgesWidth', DEFAULT_ROAD_EDGES_WIDTH) if model_ui_enabled else (False, DEFAULT_ROAD_EDGES_WIDTH)
    custom_path_edge_width, pew = self._param_float_changed('PathEdgeWidth', DEFAULT_PATH_EDGE_WIDTH) if model_ui_enabled else (False, DEFAULT_PATH_EDGE_WIDTH)

    path_width = self._path_width_to_half_m(pw) if custom_path_width else 0.9
    lane_line_width_m = self._small_distance_to_half_m(llw) if custom_lane_line_width else 0.025
    road_edge_width_m = self._small_distance_to_half_m(rew) if custom_road_edge_width else 0.025
    path_edge_width_pct = np.clip(pew / 100.0, 0.0, 1.0) if custom_path_edge_width else 0.0

    # Dynamic path width
    if model_ui_enabled and self._params.get_bool('DynamicPathWidth', default=False):
      status = ui_state.status
      if status == UIStatus.ENGAGED:
        path_width *= 1.0
      elif ui_state.always_on_lateral_active:
        path_width *= 0.75
      else:
        path_width *= 0.50

    unclipped_max_distance = np.clip(path_x_array[-1], MIN_DRAW_DISTANCE, MAX_DRAW_DISTANCE)
    unclipped_max_idx = self._get_path_length_idx(self._lane_lines[0].raw_points[:, 0], unclipped_max_distance)

    # Update lane lines using raw points
    for i, lane_line in enumerate(self._lane_lines):
      lane_line.projected_points = self._map_line_to_polygon(
        lane_line.raw_points, lane_line_width_m * self._lane_line_probs[i], 0.0, unclipped_max_idx, unclipped_max_distance, clip_by_lead=True
      )

    # Update road edges using raw points
    for road_edge in self._road_edges:
      road_edge.projected_points = self._map_line_to_polygon(road_edge.raw_points, road_edge_width_m, 0.0, unclipped_max_idx, unclipped_max_distance, clip_by_lead=True)

    # Update path using raw points
    max_distance = unclipped_max_distance
    if lead and lead.status:
      lead_d = lead.dRel * 2.0
      max_distance = np.clip(lead_d - min(lead_d * 0.35, 10.0), 0.0, max_distance)

    max_idx = self._get_path_length_idx(path_x_array, max_distance)
    self._path.projected_points = self._map_line_to_polygon(
      self._path.raw_points, path_width * (1 - path_edge_width_pct), self._path_offset_z, max_idx, max_distance, allow_invert=False
    )

    # Compute track edge vertices (outer path polygon at full width)
    self._track_edge_vertices = self._map_line_to_polygon(
      self._path.raw_points, path_width, self._path_offset_z, max_idx, max_distance, allow_invert=False
    )

    # Compute adjacent path vertices
    self._update_adjacent_paths(unclipped_max_idx, unclipped_max_distance)

    self._update_experimental_gradient()

  def _update_experimental_gradient(self):
    """Pre-calculate experimental mode gradient colors"""
    if self._use_rainbow:
      gradient_bottom, gradient_top = self._get_visible_gradient_bounds()
      self._exp_gradient = self._build_rainbow_gradient(gradient_bottom, gradient_top)
      return

    if not self._experimental_mode or not self._use_accel_path:
      return

    max_len = min(len(self._path.projected_points) // 2, len(self._acceleration_x))
    segment_colors = []
    gradient_stops = []

    i = 0
    while i < max_len:
      # Some points (screen space) are out of frame (rect space)
      track_y = self._path.projected_points[i][1]
      if track_y < self._rect.y or track_y > (self._rect.y + self._rect.height):
        i += 1
        continue

      # Calculate color based on acceleration (0 is bottom, 1 is top)
      lin_grad_point = 1 - (track_y - self._rect.y) / self._rect.height

      # speed up: 120, slow down: 0
      path_hue = np.clip(60 + self._acceleration_x[i] * 35, 0, 120)

      saturation = min(abs(self._acceleration_x[i] * 1.5), 1)
      lightness = np.interp(saturation, [0.0, 1.0], [0.95, 0.62])
      alpha = np.interp(lin_grad_point, [0.75 / 2.0, 0.75], [0.4, 0.0])

      # Use HSL to RGB conversion
      color = self._hsla_to_color(path_hue / 360.0, saturation, lightness, alpha)

      gradient_stops.append(lin_grad_point)
      segment_colors.append(color)

      # Skip a point, unless next is last
      i += 1 + (1 if (i + 2) < max_len else 0)

    # Store the gradient in the path object
    self._exp_gradient = Gradient(
      start=(0.0, 1.0),  # Bottom of path
      end=(0.0, 0.0),  # Top of path
      colors=segment_colors,
      stops=gradient_stops,
    )

  def _get_visible_gradient_bounds(self) -> tuple[float, float]:
    if self._path.projected_points.size == 0:
      return 1.0, 0.0

    polygon_y = self._path.projected_points[:, 1]
    visible_track_y = polygon_y[(polygon_y >= self._rect.y) & (polygon_y <= (self._rect.y + self._rect.height))]

    if visible_track_y.size == 0:
      return 1.0, 0.0

    gradient_bottom = np.clip((float(np.max(visible_track_y)) - self._rect.y) / self._rect.height, 0.0, 1.0)
    gradient_top = np.clip((float(np.min(visible_track_y)) - self._rect.y) / self._rect.height, 0.0, 1.0)
    return float(gradient_bottom), float(gradient_top)

  def _build_rainbow_gradient(self, gradient_bottom: float, gradient_top: float) -> Gradient:
    hue_offset = (rl.get_time() * RAINBOW_SCROLL_SPEED_DEG_PER_SEC) % 360.0
    stops = [i / (RAINBOW_GRADIENT_COLOR_COUNT - 1) for i in range(RAINBOW_GRADIENT_COLOR_COUNT)]
    colors = []

    for i, stop in enumerate(stops):
      hue_progress = i / RAINBOW_GRADIENT_COLOR_COUNT
      path_hue = (hue_progress * 360.0 - hue_offset) % 360.0
      alpha = np.interp(stop, [0.0, 1.0], [0.48, 0.18])
      colors.append(self._hsla_to_color(path_hue / 360.0, 1.0, 0.5, alpha))

    return Gradient(
      start=(0.0, gradient_bottom),
      end=(0.0, gradient_top),
      colors=colors,
      stops=stops,
    )

  def _update_lead_vehicle(self, d_rel, v_rel, point, rect):
    speed_buff, lead_buff = 10.0, 40.0

    # Calculate fill alpha
    fill_alpha = 0
    if d_rel < lead_buff:
      fill_alpha = 255 * (1.0 - (d_rel / lead_buff))
      if v_rel < 0:
        fill_alpha += 255 * (-1 * (v_rel / speed_buff))
      fill_alpha = min(fill_alpha, 255)

    # Calculate size and position
    sz = np.clip((25 * 30) / (d_rel / 3 + 30), 15.0, 30.0) * 2.35
    x = np.clip(point[0], 0.0, rect.width - sz / 2)
    y = min(point[1], rect.height - sz * 0.6)

    g_xo = sz / 5
    g_yo = sz / 10

    glow = [(x + (sz * 1.35) + g_xo, y + sz + g_yo), (x, y - g_yo), (x - (sz * 1.35) - g_xo, y + sz + g_yo)]
    chevron = [(x + (sz * 1.25), y + sz), (x, y), (x - (sz * 1.25), y + sz)]

    return LeadVehicle(glow=glow, chevron=chevron, fill_alpha=int(fill_alpha))

  def _draw_lane_lines(self):
    """Draw lane lines and road edges"""
    lane_lines_override = get_param_color(self._params, "LaneLinesColor", STOCK_LANE_LINES_COLOR.a)
    if lane_lines_override is not None:
      lane_lines_color = lane_lines_override
    elif is_stock_color_scheme(self._params):
      lane_lines_color = STOCK_LANE_LINES_COLOR
    else:
      lane_lines_color = get_theme_color("LaneLines", STOCK_LANE_LINES_COLOR)

    for i, lane_line in enumerate(self._lane_lines):
      if lane_line.projected_points.size == 0:
        continue

      alpha = np.clip(self._lane_line_probs[i], 0.0, 0.7)
      color = with_alpha(lane_lines_color, int(alpha * lane_lines_color.a))
      draw_polygon(self._rect, lane_line.projected_points, color)

    for i, road_edge in enumerate(self._road_edges):
      if road_edge.projected_points.size == 0:
        continue

      alpha = np.clip(1.0 - self._road_edge_stds[i], 0.0, 1.0)
      color = rl.Color(255, 0, 0, int(alpha * 255))
      draw_polygon(self._rect, road_edge.projected_points, color)

  def _draw_path(self, sm):
    """Draw path with dynamic coloring based on mode and throttle state."""
    if not self._path.projected_points.size:
      return

    allow_throttle = sm['longitudinalPlan'].allowThrottle or not self._longitudinal_control
    self._blend_filter.update(int(allow_throttle))

    use_rainbow = self._use_rainbow
    use_accel_path = not use_rainbow and self._use_accel_path
    if use_rainbow:
      if len(self._exp_gradient.colors) > 1:
        draw_polygon(self._rect, self._path.projected_points, gradient=self._exp_gradient)
      else:
        draw_polygon(self._rect, self._path.projected_points, rl.Color(48, 255, 156, 90))
    elif use_accel_path:
      if self._experimental_mode:
        if len(self._exp_gradient.colors) > 1:
          draw_polygon(self._rect, self._path.projected_points, gradient=self._exp_gradient)
        else:
          draw_polygon(self._rect, self._path.projected_points, rl.Color(255, 255, 255, 30))
      else:
        blend_factor = round(self._blend_filter.x * 100) / 100
        blended_colors = self._blend_colors(NO_THROTTLE_COLORS, THROTTLE_COLORS, blend_factor)
        gradient = Gradient(
          start=(0.0, 1.0),
          end=(0.0, 0.0),
          colors=blended_colors,
          stops=[0.0, 0.5, 1.0],
        )
        draw_polygon(self._rect, self._path.projected_points, gradient=gradient)
    else:
      path_color = get_visual_color(self._params, "PathColor", "Path", rl.Color(48, 255, 156, 255))
      gradient = Gradient(
        start=(0.0, 1.0),
        end=(0.0, 0.0),
        colors=[
          with_alpha(path_color, path_color.a),
          with_alpha(path_color, int(path_color.a * 0.55)),
          with_alpha(path_color, int(path_color.a * 0.10)),
        ],
        stops=[0.0, 0.5, 1.0],
      )
      draw_polygon(self._rect, self._path.projected_points, gradient=gradient)

  def _draw_lead_indicator(self, radar_state):
    # Draw lead vehicles if available
    lead_color = get_theme_color("LeadMarker", rl.Color(201, 34, 49, 255))
    leads = [radar_state.leadOne, radar_state.leadTwo]

    # Threshold for Lead 1
    threshold = self._params.get_int("LeadDetectionProbability")
    if threshold is None or threshold == 0:
      threshold = self._params.get_int("LeadDetectionThreshold")
    if threshold is None or threshold == 0:
      threshold = 50
    prob_threshold = threshold / 100.0 if threshold > 1.0 else threshold

    for i, lead in enumerate(self._lead_vehicles):
      if not lead.glow or not lead.chevron:
        continue

      # Choose color
      if i == 0 and radar_state.leadOne and radar_state.leadOne.status:
        if radar_state.leadOne.modelProb >= prob_threshold:
          color = lead_color
        else:
          color = rl.WHITE
      else:
        color = lead_color

      rl.draw_triangle_fan(lead.glow, len(lead.glow), rl.Color(218, 202, 37, 255))
      rl.draw_triangle_fan(lead.chevron, len(lead.chevron), with_alpha(color, lead.fill_alpha))

      # Draw metrics if enabled
      if self._lead_info_enabled and i < len(leads) and leads[i] and leads[i].status:
        self._draw_lead_metrics(False, lead.chevron, leads[i])

  def _update_adjacent_leads(self, starpilot_radar_state, path_x_array):
    self._adjacent_lead_vehicles = [LeadVehicle(), LeadVehicle()]
    leads = [starpilot_radar_state.leadLeft, starpilot_radar_state.leadRight]

    for i, lead_data in enumerate(leads):
      if lead_data and lead_data.status:
        d_rel, y_rel, v_rel = lead_data.dRel, lead_data.yRel, lead_data.vRel
        idx = self._get_path_length_idx(path_x_array, d_rel)
        z = self._path.raw_points[idx, 2] if idx < len(self._path.raw_points) else 0.0
        point = self._map_to_screen(d_rel, -y_rel, z + self._path_offset_z)
        if point:
          eff_d_rel = d_rel + abs(y_rel)
          self._adjacent_lead_vehicles[i] = self._update_lead_vehicle(eff_d_rel, v_rel, point, self._rect)

  def _draw_adjacent_leads(self):
    sm = ui_state.sm
    if not sm.valid.get("starpilotRadarState", False):
      return

    starpilot_radar_state = sm["starpilotRadarState"]
    lead_left = starpilot_radar_state.leadLeft
    lead_right = starpilot_radar_state.leadRight

    blue_color = rl.Color(0, 150, 255, 255)
    purple_color = rl.Color(180, 0, 255, 255)

    leads_to_draw = []
    if lead_left and lead_left.status:
      leads_to_draw.append((0, lead_left, blue_color))
    if lead_right and lead_right.status:
      leads_to_draw.append((1, lead_right, purple_color))

    for idx, lead_data, color in leads_to_draw:
      lead = self._adjacent_lead_vehicles[idx]
      if not lead.glow or not lead.chevron:
        continue

      rl.draw_triangle_fan(lead.glow, len(lead.glow), rl.Color(218, 202, 37, 255))
      rl.draw_triangle_fan(lead.chevron, len(lead.chevron), with_alpha(color, lead.fill_alpha))

      # Draw metrics if enabled
      if self._lead_info_enabled:
        self._draw_lead_metrics(True, lead.chevron, lead_data)

  def _draw_lead_metrics(self, adjacent, chevron, lead_data):
    is_metric = ui_state.is_metric
    use_si_metrics = ui_state.starpilot_toggles.get("UseSiMetrics", False)

    if is_metric or use_si_metrics:
      lead_distance_unit = "m"
      distance_conversion = 1.0
      lead_speed_unit = " m/s" if use_si_metrics else " km/h"
      speed_conversion_metrics = 1.0 if use_si_metrics else CV.MS_TO_KPH
    else:
      lead_distance_unit = "ft"
      distance_conversion = CV.METER_TO_FOOT
      lead_speed_unit = " mph"
      speed_conversion_metrics = CV.MS_TO_MPH

    y_rel = getattr(lead_data, "yRel", 0.0)
    lead_distance = lead_data.dRel + (abs(y_rel) if adjacent else 0.0)
    lead_speed = max(getattr(lead_data, "vLead", 0.0), 0.0)

    distance_string = f"{round(lead_distance * distance_conversion)}"
    speed_string = f"{round(lead_speed * speed_conversion_metrics)}"

    text_lines = []
    if adjacent:
      text_lines.append(f"{distance_string} {lead_distance_unit}")
      text_lines.append(f"{speed_string}{lead_speed_unit}")
    else:
      if self._longitudinal_control:
        plan = ui_state.sm["starpilotPlan"]
        desired_follow_distance = float(plan.desiredFollowDistance) if plan and plan.desiredFollowDistance > 0 else 0.0
        desired_distance = max(0, round(desired_follow_distance * distance_conversion))
        text_lines.append(f"{distance_string} {lead_distance_unit} (Desired: {desired_distance})")
      else:
        text_lines.append(f"{distance_string} {lead_distance_unit}")
      
      text_lines.append(f"{speed_string}{lead_speed_unit}")

      v_ego = max(ui_state.sm["carState"].vEgo, 0.0)
      time_gap = lead_distance / max(v_ego, 1.0)
      text_lines.append(f"{time_gap:.2f} seconds")

    from openpilot.system.ui.lib.application import gui_app, FontWeight
    from openpilot.selfdrive.ui.onroad.starpilot.path import _draw_text_with_outline
    font = gui_app.font(FontWeight.SEMI_BOLD)
    font_size = 24
    line_height = font_size + 2

    max_text_width = 0.0
    for line in text_lines:
      sz = measure_text_cached(font, line, font_size)
      if sz.x > max_text_width:
        max_text_width = sz.x

    centerX = chevron[1][0]
    startY = max(chevron[0][1], chevron[2][1]) + line_height + 5

    x_margin = max_text_width * 0.1
    y_margin = line_height * 0.1

    rect_x = centerX - max_text_width / 2 - x_margin
    rect_y = startY - line_height - y_margin
    rect_w = max_text_width + 2 * x_margin
    rect_h = len(text_lines) * line_height + 2 * y_margin
    text_rect = rl.Rectangle(rect_x, rect_y, rect_w, rect_h)

    collision = False
    for r in self._lead_text_rects + self._adjacent_lead_text_rects:
      if rl.check_collision_recs(text_rect, r):
        collision = True
        break

    if collision:
      return

    if adjacent:
      self._adjacent_lead_text_rects.append(text_rect)
    else:
      self._lead_text_rects.append(text_rect)

    for i, line in enumerate(text_lines):
      sz = measure_text_cached(font, line, font_size)
      line_x = centerX - sz.x / 2
      line_y = startY + (i * line_height)
      _draw_text_with_outline(line, line_x, line_y, font, font_size)

  def _draw_radar_tracks(self):
    radar_tracks_enabled = self._params.get_bool("RadarTracksUI")
    if not radar_tracks_enabled:
      return

    sm = ui_state.sm
    if not sm.valid.get("liveTracks", False):
      return

    radar_points = sm["liveTracks"].points
    if len(radar_points) == 0:
      return

    path_x_array = self._path.raw_points[:, 0]
    line_z = self._path.raw_points[:, 2]

    radius = 4.0
    red_color = rl.Color(255, 0, 0, 200)

    for point in radar_points:
      d_rel = point.dRel
      idx = self._get_path_length_idx(path_x_array, d_rel)
      z = line_z[idx] if idx < len(line_z) else 0.0

      calibrated_point = self._map_to_screen(d_rel, -point.yRel, z + self._path_offset_z)
      if calibrated_point:
        x, y = calibrated_point
        x = np.clip(x, self._rect.x, self._rect.x + self._rect.width)
        y = np.clip(y, self._rect.y, self._rect.y + self._rect.height)
        rl.draw_circle_v(rl.Vector2(x, y), radius, red_color)

  def _update_adjacent_paths(self, max_idx: int, max_distance: float):
    """Compute adjacent lane path polygons by averaging lane line pairs."""
    sm = ui_state.sm
    if sm.recv_frame.get("starpilotPlan", 0) < ui_state.started_frame:
      self._adjacent_path_vertices = [np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32)]
      return

    plan = sm["starpilotPlan"]
    lane_width_left = float(plan.laneWidthLeft) if plan.laneWidthLeft > 0 else 0.0
    lane_width_right = float(plan.laneWidthRight) if plan.laneWidthRight > 0 else 0.0

    if lane_width_left <= 0 or lane_width_right <= 0:
      self._adjacent_path_vertices = [np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32)]
      return

    # Left adjacent: average of lane_lines[0] and lane_lines[1]
    self._adjacent_path_vertices[0] = self._get_adjacent_path_polygon(
      self._lane_lines[0].raw_points, self._lane_lines[1].raw_points,
      lane_width_left / 2.0, max_idx, max_distance
    )

    # Right adjacent: average of lane_lines[2] and lane_lines[3]
    self._adjacent_path_vertices[1] = self._get_adjacent_path_polygon(
      self._lane_lines[2].raw_points, self._lane_lines[3].raw_points,
      lane_width_right / 2.0, max_idx, max_distance
    )

  def _get_adjacent_path_polygon(self, line1: np.ndarray, line2: np.ndarray, y_off: float, max_idx: int, max_distance: float) -> np.ndarray:
    if line1.shape[0] == 0 or line2.shape[0] == 0:
      return np.empty((0, 2), dtype=np.float32)

    # Use the shorter of the two lines
    min_len = min(line1.shape[0], line2.shape[0])
    if min_len == 0:
      return np.empty((0, 2), dtype=np.float32)

    # Average Y, use X and Z from line1
    avg_line = np.empty((min_len, 3), dtype=np.float32)
    avg_line[:, 0] = line1[:min_len, 0]
    avg_line[:, 1] = (line1[:min_len, 1] + line2[:min_len, 1]) / 2.0
    avg_line[:, 2] = line1[:min_len, 2]

    # Map the averaged line to a polygon using the standard path mapper
    polygon = self._map_line_to_polygon(avg_line, y_off, 0.0, max_idx, max_distance, allow_invert=True, clip_by_lead=True)

    # Ground to bottom of screen
    if polygon.shape[0] >= 4:
      height = self._rect.y + self._rect.height

      # Extend left_near (index 0) using slope from left_near → left_2nd
      p0 = polygon[0]
      p1 = polygon[1]
      dy = p0[1] - p1[1]
      if abs(dy) > 0.1:
        slope = (p0[0] - p1[0]) / dy
        p0[0] = p0[0] + (height - p0[1]) * slope
        p0[1] = height

      # Extend right_near (index -1) using slope from right_near → right_2nd
      p0 = polygon[-1]
      p1 = polygon[-2]
      dy = p0[1] - p1[1]
      if abs(dy) > 0.1:
        slope = (p0[0] - p1[0]) / dy
        p0[0] = p0[0] + (height - p0[1]) * slope
        p0[1] = height

    return polygon

  @staticmethod
  def _hex_to_color(hex_str: str) -> rl.Color:
    """Convert hex color string to rl.Color."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
      return rl.Color(
        int(hex_str[0:2], 16),
        int(hex_str[2:4], 16),
        int(hex_str[4:6], 16),
        255
      )
    return rl.Color(255, 255, 255, 255)

  @staticmethod
  def _get_path_length_idx(pos_x_array: np.ndarray, path_distance: float) -> int:
    """Get the index corresponding to the given path distance"""
    if len(pos_x_array) == 0:
      return 0
    indices = np.where(pos_x_array <= path_distance)[0]
    return indices[-1] if indices.size > 0 else 0

  def _map_to_screen(self, in_x, in_y, in_z):
    """Project a point in car space to screen space"""
    input_pt = np.array([in_x, in_y, in_z])
    pt = self._car_space_transform @ input_pt

    if abs(pt[2]) < 1e-6:
      return None

    x, y = pt[0] / pt[2], pt[1] / pt[2]

    clip = self._clip_region
    if not (clip.x <= x <= clip.x + clip.width and clip.y <= y <= clip.y + clip.height):
      return None

    return (x, y)

  def _map_line_to_polygon(self, line: np.ndarray, y_off: float, z_off: float, max_idx: int, max_distance: float, allow_invert: bool = True, clip_by_lead: bool = False) -> np.ndarray:
    """Convert 3D line to 2D polygon for rendering."""
    if line.shape[0] == 0:
      return np.empty((0, 2), dtype=np.float32)

    # Slice points and filter non-negative x-coordinates
    points = line[:max_idx + 1]

    # Interpolate around max_idx so path end is smooth (max_distance is always >= p0.x)
    if 0 < max_idx < line.shape[0] - 1:
      p0 = line[max_idx]
      p1 = line[max_idx + 1]
      x0, x1 = p0[0], p1[0]
      interp_y = np.interp(max_distance, [x0, x1], [p0[1], p1[1]])
      interp_z = np.interp(max_distance, [x0, x1], [p0[2], p1[2]])
      interp_point = np.array([max_distance, interp_y, interp_z], dtype=points.dtype)
      points = np.concatenate((points, interp_point[None, :]), axis=0)

    points = points[points[:, 0] >= 0]
    if points.shape[0] == 0:
      return np.empty((0, 2), dtype=np.float32)

    # Lead vehicle clipping to prevent drawing through/on top of lead vehicles
    if clip_by_lead:
      active_leads = []
      sm = ui_state.sm
      if sm.valid.get("radarState", False):
        rs = sm["radarState"]
        if rs.leadOne and rs.leadOne.status:
          active_leads.append(("ego", rs.leadOne))
        if rs.leadTwo and rs.leadTwo.status:
          active_leads.append(("ego", rs.leadTwo))
      if sm.valid.get("starpilotRadarState", False):
        srs = sm["starpilotRadarState"]
        if srs.leadLeft and srs.leadLeft.status:
          active_leads.append(("left", srs.leadLeft))
        if srs.leadRight and srs.leadRight.status:
          active_leads.append(("right", srs.leadRight))

      if active_leads:
        x = points[:, 0]
        y = points[:, 1]
        clipped_mask = np.zeros(len(points), dtype=bool)

        for lead_type, lead in active_leads:
          lead_x = lead.dRel
          lead_y = -lead.yRel
          y_limit = 5.0 if lead_type == "ego" else 1.8
          # Collision box for lead car: x ∈ [lead_x - 1.5, lead_x + 5.0], y ∈ [lead_y - y_limit, lead_y + y_limit]
          in_box = (x >= lead_x - 1.5) & (x <= lead_x + 5.0) & (y >= lead_y - y_limit) & (y <= lead_y + y_limit)
          clipped_mask |= in_box

        indices = np.where(clipped_mask)[0]
        if indices.size > 0:
          first_clip_idx = indices[0]
          if first_clip_idx > 0:
            # Interpolate to the exact entry boundary (lead_x - 1.5)
            p_prev = points[first_clip_idx - 1]
            p_curr = points[first_clip_idx]
            
            # Find the lead vehicle that triggered the clip
            best_lead_x = None
            for lead_type, lead in active_leads:
              lead_x = lead.dRel
              lead_y = -lead.yRel
              y_limit = 5.0 if lead_type == "ego" else 1.8
              if (lead_x - 1.5) <= p_curr[0] <= (lead_x + 5.0) and (lead_y - y_limit) <= p_curr[1] <= (lead_y + y_limit):
                best_lead_x = lead_x
                break

            if best_lead_x is not None:
              x_clip = best_lead_x - 1.5
              x0, x1 = p_prev[0], p_curr[0]
              if x1 > x0:
                t = (x_clip - x0) / (x1 - x0)
                y_clip = p_prev[1] + t * (p_curr[1] - p_prev[1])
                z_clip = p_prev[2] + t * (p_curr[2] - p_prev[2])
                interp_pt = np.array([x_clip, y_clip, z_clip], dtype=points.dtype)
                points = np.concatenate((points[:first_clip_idx], interp_pt[None, :]), axis=0)
              else:
                points = points[:first_clip_idx]
            else:
              points = points[:first_clip_idx]
          else:
            points = np.empty((0, 3), dtype=points.dtype)

    if points.shape[0] == 0:
      return np.empty((0, 2), dtype=np.float32)

    N = points.shape[0]
    # Generate left and right 3D points in one array using broadcasting
    offsets = np.array([[0, -y_off, z_off], [0, y_off, z_off]], dtype=np.float32)
    points_3d = points[None, :, :] + offsets[:, None, :]  # Shape: 2xNx3
    points_3d = points_3d.reshape(2 * N, 3)  # Shape: (2*N)x3

    # Transform all points to projected space in one operation
    proj = self._car_space_transform @ points_3d.T  # Shape: 3x(2*N)
    proj = proj.reshape(3, 2, N)
    left_proj = proj[:, 0, :]
    right_proj = proj[:, 1, :]

    # Filter points where z is sufficiently large
    valid_proj = (np.abs(left_proj[2]) >= 1e-6) & (np.abs(right_proj[2]) >= 1e-6)
    if not np.any(valid_proj):
      return np.empty((0, 2), dtype=np.float32)

    # Compute screen coordinates
    left_screen = left_proj[:2, valid_proj] / left_proj[2, valid_proj][None, :]
    right_screen = right_proj[:2, valid_proj] / right_proj[2, valid_proj][None, :]

    # Define clip region bounds
    clip = self._clip_region
    x_min, x_max = clip.x, clip.x + clip.width
    y_min, y_max = clip.y, clip.y + clip.height

    # Filter points within clip region
    left_in_clip = (
      (left_screen[0] >= x_min) & (left_screen[0] <= x_max) &
      (left_screen[1] >= y_min) & (left_screen[1] <= y_max)
    )
    right_in_clip = (
      (right_screen[0] >= x_min) & (right_screen[0] <= x_max) &
      (right_screen[1] >= y_min) & (right_screen[1] <= y_max)
    )
    both_in_clip = left_in_clip & right_in_clip

    if not np.any(both_in_clip):
      return np.empty((0, 2), dtype=np.float32)

    # Select valid and clipped points
    left_screen = left_screen[:, both_in_clip]
    right_screen = right_screen[:, both_in_clip]

    # Handle Y-coordinate inversion on hills
    if not allow_invert and left_screen.shape[1] > 1:
      y = left_screen[1, :]  # y-coordinates
      keep = y == np.minimum.accumulate(y)
      if not np.any(keep):
        return np.empty((0, 2), dtype=np.float32)
      left_screen = left_screen[:, keep]
      right_screen = right_screen[:, keep]

    return np.vstack((left_screen.T, right_screen[:, ::-1].T)).astype(np.float32)

  @staticmethod
  def _hsla_to_color(h, s, l, a):
    rgb = colorsys.hls_to_rgb(h, l, s)
    return rl.Color(
      int(rgb[0] * 255),
      int(rgb[1] * 255),
      int(rgb[2] * 255),
      int(a * 255)
    )

  def _small_distance_to_half_m(self, value: float) -> float:
    if value <= 0:
      return 0.0
    if self._is_metric:
      return value / 200.0
    return value * (CV.INCH_TO_CM / 100.0) / 2.0

  def _path_width_to_half_m(self, value: float) -> float:
    if value <= 0:
      return 0.0
    if self._is_metric:
      return value / 2.0
    return value * CV.FOOT_TO_METER / 2.0

  def _param_float_changed(self, key: str, default: float) -> tuple[bool, float]:
    value = self._params.get(key, encoding="utf-8")
    if value in (None, ""):
      return False, default
    try:
      fval = float(value)
      return (not np.isclose(fval, default)), fval
    except (TypeError, ValueError):
      return False, default

  @staticmethod
  def _blend_colors(begin_colors, end_colors, t):
    if t >= 1.0:
      return end_colors
    if t <= 0.0:
      return begin_colors

    inv_t = 1.0 - t
    return [rl.Color(
      int(inv_t * start.r + t * end.r),
      int(inv_t * start.g + t * end.g),
      int(inv_t * start.b + t * end.b),
      int(inv_t * start.a + t * end.a)
    ) for start, end in zip(begin_colors, end_colors, strict=True)]
