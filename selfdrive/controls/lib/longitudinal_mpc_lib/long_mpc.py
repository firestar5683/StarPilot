#!/usr/bin/env python3
import os
import time
import numpy as np
from cereal import log
try:
  from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
except Exception:
  # Build-time fallback for generated-code steps before full python extension availability.
  ACCEL_MIN = -3.5
  ACCEL_MAX = 2.0
from openpilot.common.constants import CV
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.controls.lib.lead_behavior import get_tracked_lead_catchup_bias, is_radarless_matched_follow_window
from openpilot.selfdrive.controls.lib.longitudinal_vehicle_tunes import get_honda_accord_11g_mpc_policy
# WARNING: imports outside of constants will not trigger a rebuild
from openpilot.selfdrive.modeld.constants import index_function, ModelConstants

if __name__ == '__main__':  # generating code
  from openpilot.third_party.acados.acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver
else:
  from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.c_generated_code.acados_ocp_solver_pyx import AcadosOcpSolverCython

from casadi import SX, vertcat

MODEL_NAME = 'long'
LONG_MPC_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(LONG_MPC_DIR, "c_generated_code")
JSON_FILE = os.path.join(LONG_MPC_DIR, "acados_ocp_long.json")

SOURCES = ['lead0', 'lead1', 'cruise', 'e2e']

X_DIM = 3
U_DIM = 1
PARAM_DIM = 6
COST_E_DIM = 5
COST_DIM = COST_E_DIM + 1
CONSTR_DIM = 4

# ===== VOACC SPEED-BASED TUNING PARAMETERS =====
# City: Emergency-responsive | Highway: Rubber-banding prevention
# Speed ranges: [0-35, 35-55, 55-70, 70+ mph]

# SPEED BREAKPOINTS (mph)
SPEED_BREAKPOINTS = [0, 35, 55, 70]  # 4 ranges: 0-35, 35-55, 55-70, 70+

# ===== CHANGE THESE VALUES FOR DIFFERENT SPEEDS =====

# RESPONSIVENESS TO LEAD CARS (Lower = More responsive, Higher = More stable)
# [City Emergency, Urban Hwy, Rural Hwy, High Speed]
X_EGO_OBSTACLE_COSTS = [3.0, 3.0, 2.5, 2.0]  # Less aggressive at low speeds, closer to original

# JERK CONTROL (Lower = More jerky/responsive, Higher = Smoother/conservative)
# [City Emergency, Urban Hwy, Rural Hwy, High Speed]
J_EGO_COSTS = [5.0, 4.75, 4.5, 4.0]  # Reverted to original 5.0 at low speeds

# ACCELERATION CHANGE PENALTIES (Lower = More responsive, Higher = Smoother)
# [City Emergency, Urban Hwy, Rural Hwy, High Speed]
A_CHANGE_COSTS = [200, 195, 180, 170]  # Reverted to original 200 at low speeds

# SMOOTHING FILTERS - Speed-adaptive for optimal responsiveness
# Lower = More responsive, Higher = Smoother
LEAD_FILTER_TIME_LOW = 0.8   # Under 40 mph: Fast response for city emergency braking
LEAD_FILTER_TIME_HIGH = 1.2  # Over 40 mph: Faster response to prevent highway gaps
SPEED_FILTER_THRESHOLD = 40 * CV.MPH_TO_MS  # 40 mph threshold
DUPLICATE_VISION_LEAD_FILTER_TIME = 0.15

# DISTANCE ADAPTATION STRENGTH (How much penalties increase when close to lead)
# [City, Urban Hwy, Rural Hwy, High Speed]
DIST_ADAPTS = [0.04, 0.06, 0.06, 0.05]  # Balanced across speeds

# ===== END TUNING PARAMETERS =====

FAR_RADAR_LEAD_ACCEL_TAPER_MAX = 1.0
FAR_RADAR_LEAD_ACCEL_TAPER_MAX_CLOSING = 2.5
FAR_RADAR_LEAD_ACCEL_TAPER_MIN_GAP_EXCESS = 8.0
FAR_RADAR_LEAD_ACCEL_TAPER_MIN_GAP_GAIN = 0.25
FAR_RADAR_LEAD_ACCEL_TAPER_FULL_GAP_EXCESS = 25.0
FAR_RADAR_LEAD_ACCEL_TAPER_FULL_GAP_GAIN = 0.9
STABLE_FOLLOW_CRUISE_MIN_SPEED = 8.0
STABLE_FOLLOW_CRUISE_HYSTERESIS_MIN = 4.0
STABLE_FOLLOW_CRUISE_HYSTERESIS_GAIN = 0.14
STABLE_FOLLOW_CRUISE_MAX_REL_SPEED = 2.5
STABLE_FOLLOW_CRUISE_MIN_HEADWAY = 0.95
STABLE_FOLLOW_CRUISE_HEADWAY_BELOW_TARGET = 0.35
STABLE_FOLLOW_CRUISE_HEADWAY_ABOVE_TARGET = 0.90
STABLE_FOLLOW_CRUISE_MAX_LEAD_BRAKE = 0.35
STABLE_FOLLOW_CRUISE_PULLAWAY_MAX_REL_SPEED = 2.0
STABLE_FOLLOW_CRUISE_PULLAWAY_MAX_HEADWAY_MARGIN = 0.35
STABLE_FOLLOW_CRUISE_PULLAWAY_MIN_HEADWAY_MARGIN = -0.10
STABLE_FOLLOW_CRUISE_PULLAWAY_HYSTERESIS_MAX = 1.75
VISION_FOLLOW_CRUISE_HOLD_MIN_MODEL_PROB = 0.95
VISION_FOLLOW_CRUISE_HOLD_MAX_CRUISE_ADVANTAGE = 2.0
NEAR_DUPLICATE_LEAD_SOURCE_MIN_SPEED = 4.0
NEAR_DUPLICATE_IDENTICAL_RADAR_SOURCE_MIN_SPEED = 10.0
NEAR_DUPLICATE_LEAD_SOURCE_MIN_MODEL_PROB = 0.9
NEAR_DUPLICATE_LEAD_SOURCE_MAX_LEAD_BRAKE = 0.35
NEAR_DUPLICATE_LEAD_SOURCE_MAX_DREL_DIFF = 1.5
NEAR_DUPLICATE_LEAD_SOURCE_MAX_VREL_DIFF = 0.35
NEAR_DUPLICATE_LEAD_SOURCE_HYSTERESIS_MIN = 1.25
NEAR_DUPLICATE_LEAD_SOURCE_HYSTERESIS_MAX = 2.25
NEAR_DUPLICATE_IDENTICAL_RADAR_SOURCE_KEEP_MARGIN = 0.35
IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MIN_SPEED = 10.0
IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_HEADWAY_ABOVE_TARGET = 0.40
IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_LEAD_BRAKE = 0.25
IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_PULLAWAY_SPEED = 1.5
IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_CRUISE_ADVANTAGE = 10.0
IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MIN_SPEED = 15.0
IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_HEADWAY_ABOVE_TARGET = 0.55
IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MIN_HEADWAY_BELOW_TARGET = -0.15
IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_LEAD_BRAKE = 0.25
IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_PULLAWAY_SPEED = 0.75
IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX = 10.0

# Function to get parameter value based on current speed
def get_speed_based_param(speed_mph, param_array):
  """Get parameter value based on current speed using smooth interpolation"""
  return float(np.interp(speed_mph, SPEED_BREAKPOINTS, param_array))

# Current active values (set based on speed)
X_EGO_OBSTACLE_COST = 2.75
J_EGO_COST = 5.5
A_CHANGE_COST = 250.0
LEAD_FILTER_TIME = 2.0
DIST_ADAPT = 0.06

X_EGO_COST = 0.
V_EGO_COST = 0.
A_EGO_COST = 0.
DANGER_ZONE_COST = 100.
CRASH_DISTANCE = .25
LEAD_DANGER_FACTOR = 0.75
LIMIT_COST = 1e6
ACADOS_SOLVER_TYPE = 'SQP_RTI'
# Default lead acceleration decay set to 50% at 1s
LEAD_ACCEL_TAU = 1.5
FCW_MIN_MODEL_PROB = 0.9
FCW_MIN_CLOSING_SPEED = 0.5
FCW_MAX_TTC = 4.0
MODEL_LEAD_TRAJECTORY_MAX_LEAD_BRAKE = 0.5
MODEL_LEAD_TRAJECTORY_MAX_CLOSING_TTC = 7.0


# Fewer timestamps don't hurt performance and lead to
# much better convergence of the MPC with low iterations
N = 12
MAX_T = 10.0
T_IDXS_LST = [index_function(idx, max_val=MAX_T, max_idx=N) for idx in range(N+1)]

T_IDXS = np.array(T_IDXS_LST)
FCW_IDXS = T_IDXS < 5.0
T_DIFFS = np.diff(T_IDXS, prepend=[0.])
LEAD_T_IDXS_MODEL = np.asarray(ModelConstants.LEAD_T_IDXS, dtype=np.float64)
COMFORT_BRAKE = 2.5
STOP_DISTANCE = 6.0


def build_model_lead_trajectory(model_lead, radar_lead, v_ego):
  """Build a model-predicted lead path while preserving the raw h=0 anchor."""
  if model_lead is None or radar_lead is None or not bool(getattr(radar_lead, "status", False)):
    return None

  try:
    if float(model_lead.prob) <= 0.5:
      return None
    model_x = np.asarray(model_lead.x, dtype=np.float64)
    model_v = np.asarray(model_lead.v, dtype=np.float64)
  except (AttributeError, TypeError, ValueError):
    return None

  expected_len = len(LEAD_T_IDXS_MODEL)
  if model_x.shape != (expected_len,) or model_v.shape != (expected_len,):
    return None
  if not np.all(np.isfinite(model_x)) or not np.all(np.isfinite(model_v)):
    return None

  raw_d_rel = float(getattr(radar_lead, "dRel", float("nan")))
  raw_v_lead = float(getattr(radar_lead, "vLead", float("nan")))
  if not np.isfinite(raw_d_rel) or not np.isfinite(raw_v_lead):
    return None

  # The model path is a comfort prediction, not the raw safety measurement.
  # When the measured lead is already braking or the gap is closing quickly,
  # keep the legacy raw-lead path so an optimistic model horizon cannot delay
  # the first braking response.
  raw_lead_brake = max(0.0, -float(getattr(radar_lead, "aLeadK", 0.0)))
  closing_speed = max(0.0, float(v_ego) - raw_v_lead)
  ttc = raw_d_rel / max(closing_speed, 1e-3) if closing_speed > 0.1 else float("inf")
  if (raw_lead_brake > MODEL_LEAD_TRAJECTORY_MAX_LEAD_BRAKE or
      (closing_speed > 0.75 and ttc < MODEL_LEAD_TRAJECTORY_MAX_CLOSING_TTC)):
    return None

  # The model contributes future deltas only. This preserves raw lead source
  # selection and keeps the current lead distance/speed safety anchor intact.
  x_lead_traj = raw_d_rel + (model_x - model_x[0])
  v_lead_traj = raw_v_lead + (model_v - model_v[0])
  v_lead_traj = np.clip(v_lead_traj, 0.0, 1e8)

  # Match the existing MPC convergence guard using the physical brake limit.
  v_ego = float(v_ego)
  min_x_lead = ((v_ego + v_lead_traj[0]) / 2.0) * (v_ego - v_lead_traj[0]) / (-ACCEL_MIN * 2.0)
  x_lead_traj[0] = max(x_lead_traj[0], min_x_lead)

  x_lead_mpc = np.maximum.accumulate(np.interp(T_IDXS, LEAD_T_IDXS_MODEL, x_lead_traj))
  v_lead_mpc = np.interp(T_IDXS, LEAD_T_IDXS_MODEL, v_lead_traj)
  return np.column_stack((x_lead_mpc, v_lead_mpc))


def should_trigger_planner_fcw(lead, v_ego: float) -> bool:
  if lead is None or not lead.status or float(getattr(lead, "modelProb", 0.0)) <= FCW_MIN_MODEL_PROB:
    return False

  closing_speed = max(0.0, float(v_ego) - float(getattr(lead, "vLead", 0.0)))
  if closing_speed < FCW_MIN_CLOSING_SPEED:
    return False

  ttc = max(0.0, float(getattr(lead, "dRel", 0.0))) / max(closing_speed, 1e-3)
  return ttc < FCW_MAX_TTC

def get_jerk_factor(aggressive_jerk_acceleration=0.5, aggressive_jerk_danger=0.5, aggressive_jerk_speed=0.5,
                    standard_jerk_acceleration=1.0, standard_jerk_danger=1.0, standard_jerk_speed=1.0,
                    relaxed_jerk_acceleration=1.0, relaxed_jerk_danger=1.0, relaxed_jerk_speed=1.0,
                    custom_personalities=False, personality=log.LongitudinalPersonality.standard):
  if custom_personalities:
    if personality==log.LongitudinalPersonality.relaxed:
      return relaxed_jerk_acceleration, relaxed_jerk_danger, relaxed_jerk_speed
    elif personality==log.LongitudinalPersonality.standard:
      return standard_jerk_acceleration, standard_jerk_danger, standard_jerk_speed
    elif personality==log.LongitudinalPersonality.aggressive:
      return aggressive_jerk_acceleration, aggressive_jerk_danger, aggressive_jerk_speed
    else:
      raise NotImplementedError("Longitudinal personality not supported")
  else:
    if personality==log.LongitudinalPersonality.relaxed:
      return 1.0, 1.0, 1.0
    elif personality==log.LongitudinalPersonality.standard:
      return 1.0, 1.0, 1.0
    elif personality==log.LongitudinalPersonality.aggressive:
      return 0.5, 0.5, 0.5
    else:
      raise NotImplementedError("Longitudinal personality not supported")


def get_T_FOLLOW(aggressive_follow=1.25, standard_follow=1.45, relaxed_follow=1.75, custom_personalities=False, personality=log.LongitudinalPersonality.standard):
  if custom_personalities:
    if personality==log.LongitudinalPersonality.relaxed:
      return relaxed_follow
    elif personality==log.LongitudinalPersonality.standard:
      return standard_follow
    elif personality==log.LongitudinalPersonality.aggressive:
      return aggressive_follow
    else:
      raise NotImplementedError("Longitudinal personality not supported")
  else:
    if personality==log.LongitudinalPersonality.relaxed:
      return 1.75
    elif personality==log.LongitudinalPersonality.standard:
      return 1.45
    elif personality==log.LongitudinalPersonality.aggressive:
      return 1.25
    else:
      raise NotImplementedError("Longitudinal personality not supported")

def get_stopped_equivalence_factor(v_lead):
  return (v_lead**2) / (2 * COMFORT_BRAKE)

def get_safe_obstacle_distance(v_ego, t_follow):
  return (v_ego**2) / (2 * COMFORT_BRAKE) + t_follow * v_ego + STOP_DISTANCE

def desired_follow_distance(v_ego, v_lead, t_follow=None):
  if t_follow is None:
    t_follow = get_T_FOLLOW()
  return get_safe_obstacle_distance(v_ego, t_follow) - get_stopped_equivalence_factor(v_lead)


def soften_far_radar_lead_accel(d_rel, v_lead, a_lead, v_ego, t_follow, *, radar=True):
  if not radar or a_lead >= 0.0:
    return float(a_lead)

  desired_gap = float(desired_follow_distance(v_ego, v_lead, t_follow))
  closing_speed = max(0.0, float(v_ego) - float(v_lead))
  gap_excess = float(d_rel) - desired_gap

  taper_start = max(FAR_RADAR_LEAD_ACCEL_TAPER_MIN_GAP_EXCESS,
                    FAR_RADAR_LEAD_ACCEL_TAPER_MIN_GAP_GAIN * float(v_ego))
  if gap_excess <= taper_start or closing_speed >= FAR_RADAR_LEAD_ACCEL_TAPER_MAX_CLOSING:
    return float(a_lead)

  taper_scale = max(FAR_RADAR_LEAD_ACCEL_TAPER_FULL_GAP_EXCESS,
                    FAR_RADAR_LEAD_ACCEL_TAPER_FULL_GAP_GAIN * float(v_ego))
  distance_factor = float(np.clip((gap_excess - taper_start) / taper_scale, 0.0, 1.0))
  closing_factor = float(np.clip((FAR_RADAR_LEAD_ACCEL_TAPER_MAX_CLOSING - closing_speed) /
                                 FAR_RADAR_LEAD_ACCEL_TAPER_MAX_CLOSING, 0.0, 1.0))
  taper = FAR_RADAR_LEAD_ACCEL_TAPER_MAX * distance_factor * closing_factor
  return float(a_lead * (1.0 - taper))


def gen_long_model():
  model = AcadosModel()
  model.name = MODEL_NAME

  # set up states & controls
  x_ego = SX.sym('x_ego')
  v_ego = SX.sym('v_ego')
  a_ego = SX.sym('a_ego')
  model.x = vertcat(x_ego, v_ego, a_ego)

  # controls
  j_ego = SX.sym('j_ego')
  model.u = vertcat(j_ego)

  # xdot
  x_ego_dot = SX.sym('x_ego_dot')
  v_ego_dot = SX.sym('v_ego_dot')
  a_ego_dot = SX.sym('a_ego_dot')
  model.xdot = vertcat(x_ego_dot, v_ego_dot, a_ego_dot)

  # live parameters
  a_min = SX.sym('a_min')
  a_max = SX.sym('a_max')
  x_obstacle = SX.sym('x_obstacle')
  prev_a = SX.sym('prev_a')
  lead_t_follow = SX.sym('lead_t_follow')
  lead_danger_factor = SX.sym('lead_danger_factor')
  model.p = vertcat(a_min, a_max, x_obstacle, prev_a, lead_t_follow, lead_danger_factor)

  # dynamics model
  f_expl = vertcat(v_ego, a_ego, j_ego)
  model.f_impl_expr = model.xdot - f_expl
  model.f_expl_expr = f_expl
  return model


def gen_long_ocp():
  ocp = AcadosOcp()
  ocp.model = gen_long_model()

  Tf = T_IDXS[-1]

  # set dimensions
  ocp.dims.N = N

  # set cost module
  ocp.cost.cost_type = 'NONLINEAR_LS'
  ocp.cost.cost_type_e = 'NONLINEAR_LS'

  QR = np.zeros((COST_DIM, COST_DIM))
  Q = np.zeros((COST_E_DIM, COST_E_DIM))

  ocp.cost.W = QR
  ocp.cost.W_e = Q

  x_ego, v_ego, a_ego = ocp.model.x[0], ocp.model.x[1], ocp.model.x[2]
  j_ego = ocp.model.u[0]

  a_min, a_max = ocp.model.p[0], ocp.model.p[1]
  x_obstacle = ocp.model.p[2]
  prev_a = ocp.model.p[3]
  lead_t_follow = ocp.model.p[4]
  lead_danger_factor = ocp.model.p[5]

  ocp.cost.yref = np.zeros((COST_DIM, ))
  ocp.cost.yref_e = np.zeros((COST_E_DIM, ))

  desired_dist_comfort = get_safe_obstacle_distance(v_ego, lead_t_follow)

  # The main cost in normal operation is how close you are to the "desired" distance
  # from an obstacle at every timestep. This obstacle can be a lead car
  # or other object. In e2e mode we can use x_position targets as a cost
  # instead.
  accel_change = a_ego - prev_a
  costs = [((x_obstacle - x_ego) - (desired_dist_comfort)) / (v_ego + 10.),
           x_ego,
           v_ego,
           a_ego,
           accel_change,
           j_ego]
  ocp.model.cost_y_expr = vertcat(*costs)
  ocp.model.cost_y_expr_e = vertcat(*costs[:-1])

  # Constraints on speed, acceleration and desired distance to
  # the obstacle, which is treated as a slack constraint so it
  # behaves like an asymmetrical cost.
  constraints = vertcat(v_ego,
                        (a_ego - a_min),
                        (a_max - a_ego),
                        ((x_obstacle - x_ego) - lead_danger_factor * (desired_dist_comfort)) / (v_ego + 10.))
  ocp.model.con_h_expr = constraints

  x0 = np.zeros(X_DIM)
  ocp.constraints.x0 = x0
  ocp.parameter_values = np.array([-1.2, 1.2, 0.0, 0.0, get_T_FOLLOW(), LEAD_DANGER_FACTOR])


  # We put all constraint cost weights to 0 and only set them at runtime
  cost_weights = np.zeros(CONSTR_DIM)
  ocp.cost.zl = cost_weights
  ocp.cost.Zl = cost_weights
  ocp.cost.Zu = cost_weights
  ocp.cost.zu = cost_weights

  ocp.constraints.lh = np.zeros(CONSTR_DIM)
  ocp.constraints.uh = 1e4*np.ones(CONSTR_DIM)
  ocp.constraints.idxsh = np.arange(CONSTR_DIM)

  # The HPIPM solver can give decent solutions even when it is stopped early
  # Which is critical for our purpose where compute time is strictly bounded
  # We use HPIPM in the SPEED_ABS mode, which ensures fastest runtime. This
  # does not cause issues since the problem is well bounded.
  ocp.solver_options.qp_solver = 'PARTIAL_CONDENSING_HPIPM'
  ocp.solver_options.hessian_approx = 'GAUSS_NEWTON'
  ocp.solver_options.integrator_type = 'ERK'
  ocp.solver_options.nlp_solver_type = ACADOS_SOLVER_TYPE
  ocp.solver_options.qp_solver_cond_N = 1

  # More iterations take too much time and less lead to inaccurate convergence in
  # some situations. Ideally we would run just 1 iteration to ensure fixed runtime.
  ocp.solver_options.qp_solver_iter_max = 10
  ocp.solver_options.qp_tol = 1e-3

  # set prediction horizon
  ocp.solver_options.tf = Tf
  ocp.solver_options.shooting_nodes = T_IDXS

  ocp.code_export_directory = EXPORT_DIR
  return ocp


class LongitudinalMpc:
  def __init__(self, mode='acc', dt=DT_MDL, CP=None, solver=None):
    self.mode = mode
    self.dt = dt
    self.honda_accord_11g_policy = get_honda_accord_11g_mpc_policy(CP)
    self.solver = solver if solver is not None else AcadosOcpSolverCython(MODEL_NAME, ACADOS_SOLVER_TYPE, N)
    self.source = SOURCES[2]
    # Initialize smoothing filters with default time constants
    self.current_filter_time = LEAD_FILTER_TIME_LOW
    self.lead_a_filter = FirstOrderFilter(0.0, self.current_filter_time, self.dt)
    self.lead_v_filter = FirstOrderFilter(0.0, self.current_filter_time, self.dt)
    self.duplicate_lead_x_filters = [FirstOrderFilter(0.0, 0.0, self.dt, initialized=False) for _ in range(2)]
    self.duplicate_lead_a_filters = [FirstOrderFilter(0.0, 0.0, self.dt, initialized=False) for _ in range(2)]
    self.duplicate_lead_v_filters = [FirstOrderFilter(0.0, 0.0, self.dt, initialized=False) for _ in range(2)]
    # Slew-limited filter factor to avoid abrupt 0.50↔1.00 jumps
    self.filter_time_factor = 1.0
    self.prev_filter_time_factor = 1.0
    self.slew_per_sec = 1.0
    # Instance variables to avoid global modifications
    self.current_x_ego_cost = X_EGO_OBSTACLE_COSTS[0]
    self.current_j_ego_cost = J_EGO_COSTS[0]
    self.current_a_change_cost = A_CHANGE_COSTS[0]
    self.current_dist_adapt = DIST_ADAPTS[0]
    # Initialize acceleration limits to prevent AttributeError
    self.cruise_min_a = ACCEL_MIN
    self.max_a = min(ACCEL_MAX, 1.2)
    self.reset()

  def reset(self):
    # self.solver = AcadosOcpSolverCython(MODEL_NAME, ACADOS_SOLVER_TYPE, N)
    self.solver.reset()
    # self.solver.options_set('print_level', 2)
    self.v_solution = np.zeros(N+1)
    self.a_solution = np.zeros(N+1)
    self.prev_a = np.array(self.a_solution)
    self.j_solution = np.zeros(N)
    self.yref = np.zeros((N+1, COST_DIM))
    for i in range(N):
      self.solver.cost_set(i, "yref", self.yref[i])
    self.solver.cost_set(N, "yref", self.yref[N][:COST_E_DIM])
    self.x_sol = np.zeros((N+1, X_DIM))
    self.u_sol = np.zeros((N,1))
    self.lead_xv_0 = np.zeros((N+1, 2))
    self.lead_xv_1 = np.zeros((N+1, 2))
    self.params = np.zeros((N+1, PARAM_DIM))
    for i in range(N+1):
      self.solver.set(i, 'x', np.zeros(X_DIM))
    self.last_cloudlog_t = 0
    self.status = False
    self.crash_cnt = 0.0
    self.solution_status = 0
    # timers
    self.solve_time = 0.0
    self.time_qp_solution = 0.0
    self.time_linearization = 0.0
    self.time_integrator = 0.0
    self.x0 = np.zeros(X_DIM)
    for lead_filter in (*self.duplicate_lead_x_filters, *self.duplicate_lead_a_filters, *self.duplicate_lead_v_filters):
      lead_filter.x = 0.0
      lead_filter.initialized = False
    self.set_weights()

  def set_cost_weights(self, cost_weights, constraint_cost_weights):
    W = np.asfortranarray(np.diag(cost_weights))
    for i in range(N):
      # TODO don't hardcode A_CHANGE_COST idx
      # reduce the cost on (a-a_prev) later in the horizon.
      W[4,4] = cost_weights[4] * np.interp(T_IDXS[i], [0.0, 1.0, 2.0], [1.0, 1.0, 0.0])
      self.solver.cost_set(i, 'W', W)
    # Setting the slice without the copy make the array not contiguous,
    # causing issues with the C interface.
    self.solver.cost_set(N, 'W', np.copy(W[:COST_E_DIM, :COST_E_DIM]))

    # Set L2 slack cost on lower bound constraints
    Zl = np.array(constraint_cost_weights)
    for i in range(N):
      self.solver.cost_set(i, 'Zl', Zl)

  def set_weights(self, acceleration_jerk=1.0, danger_jerk=1.0, speed_jerk=1.0, prev_accel_constraint=True,
                  personality=log.LongitudinalPersonality.standard, v_ego=0.0, lead_dist=50.0,
                  uncertainty=0.0, accel_reengage=False, panic_bypass=False,
                  filter_time_factor_floor=0.0):
    if self.honda_accord_11g_policy is not None:
      policy = self.honda_accord_11g_policy
      jerk_factor = get_jerk_factor(personality=personality)[0]
      self.current_x_ego_cost = policy["obstacle_cost"]
      self.current_j_ego_cost = policy["jerk_cost"]
      self.current_a_change_cost = policy["accel_change_cost"]
      self.current_dist_adapt = 0.0
      a_change_cost = jerk_factor * policy["accel_change_cost"] if prev_accel_constraint else 0.0
      cost_weights = [policy["obstacle_cost"], X_EGO_COST, V_EGO_COST, A_EGO_COST,
                      a_change_cost, jerk_factor * policy["jerk_cost"]]
      self.set_cost_weights(cost_weights, [LIMIT_COST, LIMIT_COST, LIMIT_COST, DANGER_ZONE_COST])
      return

    # Update parameters based on current speed with interpolation for smooth scaling
    speed_mph = v_ego * CV.MS_TO_MPH  # Convert m/s to mph

    # Use speed-based parameters for smooth scaling across all breakpoints
    self.current_x_ego_cost = get_speed_based_param(speed_mph, X_EGO_OBSTACLE_COSTS)
    self.current_j_ego_cost = get_speed_based_param(speed_mph, J_EGO_COSTS)
    self.current_a_change_cost = get_speed_based_param(speed_mph, A_CHANGE_COSTS)

    # For dist_adapt, start from 0.0 under low speeds while enabling full smooth transitions
    dist_adapt_array = [0.0, DIST_ADAPTS[1], DIST_ADAPTS[2], DIST_ADAPTS[3]]
    self.current_dist_adapt = get_speed_based_param(speed_mph, dist_adapt_array)

    # Update filter time constants with interp and recreate filters if needed
    if speed_mph < 47:
        self.current_filter_time = 0.0
    else:
        self.current_filter_time = np.interp(speed_mph, [47, 65], [0.0, LEAD_FILTER_TIME_HIGH])
    if abs(self.current_filter_time - getattr(self, 'prev_filter_time', 0)) > 0.1:  # Only update if significant change
      # Recreate filters with new time constant while preserving current values
      current_a = self.lead_a_filter.x if hasattr(self.lead_a_filter, 'x') else 0.0
      current_v = self.lead_v_filter.x if hasattr(self.lead_v_filter, 'x') else 0.0
      self.lead_a_filter = FirstOrderFilter(current_a, self.current_filter_time, self.dt)
      self.lead_v_filter = FirstOrderFilter(current_v, self.current_filter_time, self.dt)
      self.prev_filter_time = self.current_filter_time
    # Adaptive jerk factors for distance with interp scaling
    dist_factor = 1.0 + self.current_dist_adapt * (20.0 / max(lead_dist, 5.0))
    acceleration_jerk *= dist_factor
    danger_jerk *= dist_factor
    speed_jerk *= dist_factor

    # Scene complexity adjustment based on model uncertainty
    # Target factor from uncertainty
    if uncertainty <= 0.45:
      tgt_factor = 1.0
    elif uncertainty >= 0.70:
      tgt_factor = 0.0
    else:
      tgt_factor = float(np.interp(uncertainty, [0.45, 0.70], [1.0, 0.30]))

    if accel_reengage:
      tgt_factor = min(tgt_factor, 0.5)

    # Hard bypass of smoothing when approaching fast or magnitude trips
    if panic_bypass:
      tgt_factor = 0.0
    else:
      tgt_factor = max(tgt_factor, float(filter_time_factor_floor))

    # Slew-limit changes to avoid step-wise filter jumps
    if panic_bypass:
      # A real closing hazard must never wait for the comfort filter to unwind.
      self.filter_time_factor = 0.0
    else:
      max_step = self.slew_per_sec * self.dt
      delta = np.clip(tgt_factor - self.filter_time_factor, -max_step, max_step)
      self.filter_time_factor += float(delta)

    # When uncertainty is moderately elevated, allow accel but cap jerk by increasing jerk cost
    if 0.45 <= uncertainty < 0.60:
      scale = float(np.interp(uncertainty, [0.45, 0.60], [1.2, 1.5]))
      speed_jerk *= scale

    if self.mode == 'acc':
      a_change_cost = acceleration_jerk if prev_accel_constraint else 0
      cost_weights = [self.current_x_ego_cost, X_EGO_COST, V_EGO_COST, A_EGO_COST, a_change_cost, speed_jerk]
      constraint_cost_weights = [LIMIT_COST, LIMIT_COST, LIMIT_COST, danger_jerk]
    elif self.mode == 'blended':
      a_change_cost = 40.0 if prev_accel_constraint else 0
      cost_weights = [0., 0.1, 0.2, 5.0, a_change_cost, 1.0]
      constraint_cost_weights = [LIMIT_COST, LIMIT_COST, LIMIT_COST, danger_jerk]
    else:
      raise NotImplementedError(f'Planner mode {self.mode} not recognized in planner cost set')
    self.set_cost_weights(cost_weights, constraint_cost_weights)

    # Adjust filter time constants for complex scenes
    filter_time_factor = float(self.filter_time_factor)
    if abs(filter_time_factor - getattr(self, 'prev_filter_time_factor', 1.0)) > 0.05:
      new_filter_time = self.current_filter_time * filter_time_factor
      current_a = self.lead_a_filter.x if hasattr(self.lead_a_filter, 'x') else 0.0
      current_v = self.lead_v_filter.x if hasattr(self.lead_v_filter, 'x') else 0.0
      self.lead_a_filter = FirstOrderFilter(current_a, new_filter_time, self.dt)
      self.lead_v_filter = FirstOrderFilter(current_v, new_filter_time, self.dt)
      self.prev_filter_time_factor = filter_time_factor

  def set_cur_state(self, v, a):
    v_prev = self.x0[1]
    self.x0[1] = v
    self.x0[2] = a
    if abs(v_prev - v) > 2.:  # probably only helps if v < v_prev
      for i in range(N+1):
        self.solver.set(i, 'x', self.x0)

  @staticmethod
  def extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau, v_ego=0.0, *, raw_decay=False):
    if raw_decay:
      a_lead_traj = a_lead * np.exp(-a_lead_tau * (T_IDXS ** 2) / 2.0)
      v_lead_traj = np.clip(v_lead + np.cumsum(T_DIFFS * a_lead_traj), 0.0, 1e8)
      x_lead_traj = x_lead + np.cumsum(T_DIFFS * v_lead_traj)
      return np.column_stack((x_lead_traj, v_lead_traj))

    speed_mph = v_ego * CV.MS_TO_MPH
    bp = [0, 20, 35]
    exp_weight = np.interp(speed_mph, bp, [1.0, 1.0, 0.0])  # Full exp at <20, blend to constant at 35

    if exp_weight > 0:
      # Exponential decay component
      a_lead_traj_exp = a_lead * np.exp(-a_lead_tau * (T_IDXS**2)/2.)
      v_lead_traj_exp = np.clip(v_lead + np.cumsum(T_DIFFS * a_lead_traj_exp), 0.0, 1e8)
      x_lead_traj_exp = x_lead + np.cumsum(T_DIFFS * v_lead_traj_exp)
    else:
      x_lead_traj_exp = np.zeros_like(T_IDXS)
      v_lead_traj_exp = np.zeros_like(T_IDXS)

    # Constant acceleration component
    v_lead_traj_const = np.clip(v_lead + a_lead * T_IDXS, 0.0, 1e8)
    x_lead_traj_const = x_lead + v_lead * T_IDXS + 0.5 * a_lead * T_IDXS**2

    # Blend based on weight
    v_lead_traj = exp_weight * v_lead_traj_exp + (1 - exp_weight) * v_lead_traj_const
    x_lead_traj = exp_weight * x_lead_traj_exp + (1 - exp_weight) * x_lead_traj_const

    lead_xv = np.column_stack((x_lead_traj, v_lead_traj))
    return lead_xv

  def process_lead(self, lead, tracking_lead=True, t_follow=None, *, lead_index=0,
                   smooth_duplicate_vision=False, model_lead=None):
    v_ego = self.x0[1]
    lead_active = lead is not None and lead.status and tracking_lead
    if self.honda_accord_11g_policy is not None:
      if lead_active:
        x_lead = lead.dRel
        v_lead = lead.vLead
        a_lead = lead.aLeadK
        a_lead_tau = lead.aLeadTau
      else:
        x_lead = 50.0
        v_lead = v_ego + 10.0
        a_lead = 0.0
        a_lead_tau = self.honda_accord_11g_policy["lead_accel_tau"]

      min_x_lead = ((v_ego + v_lead) / 2) * (v_ego - v_lead) / (-ACCEL_MIN * 2)
      x_lead = np.clip(x_lead, min_x_lead, 1e8)
      v_lead = np.clip(v_lead, 0.0, 1e8)
      a_lead = np.clip(a_lead, -10.0, 5.0)
      return self.extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau, raw_decay=True)

    if lead_active:
      model_lead_xv = build_model_lead_trajectory(model_lead, lead, v_ego)
      if model_lead_xv is not None:
        return model_lead_xv

    if lead_active:
      x_lead = lead.dRel
      v_lead = lead.vLead
      a_lead = lead.aLeadK
      a_lead_tau = lead.aLeadTau
      a_lead = soften_far_radar_lead_accel(x_lead, v_lead, a_lead, v_ego,
                                           get_T_FOLLOW() if t_follow is None else t_follow,
                                           radar=bool(getattr(lead, "radar", False)))
    else:
      # Fake a fast lead car, so mpc can keep running in the same mode
      x_lead = 50.0
      v_lead = v_ego + 10.0
      a_lead = 0.0
      a_lead_tau = LEAD_ACCEL_TAU

    # MPC will not converge if immediate crash is expected.
    # Bound this by physical hard-brake capability, not cruise comfort decel.
    min_x_lead = ((v_ego + v_lead)/2) * (v_ego - v_lead) / (-ACCEL_MIN * 2)
    x_lead = np.clip(x_lead, min_x_lead, 1e8)
    v_lead = np.clip(v_lead, 0.0, 1e8)
    a_lead = np.clip(a_lead, -10., 5.)
    if lead_active and smooth_duplicate_vision and not bool(getattr(lead, "radar", False)):
      # Keep the baseline filter synchronized so leaving this narrow comfort
      # path cannot introduce a state discontinuity.
      self.lead_a_filter.update(a_lead)
      self.lead_v_filter.update(v_lead)

      filter_time = self.current_filter_time
      filter_time = max(filter_time, DUPLICATE_VISION_LEAD_FILTER_TIME)
      filter_time *= self.filter_time_factor

      x_filter = self.duplicate_lead_x_filters[lead_index]
      a_filter = self.duplicate_lead_a_filters[lead_index]
      v_filter = self.duplicate_lead_v_filters[lead_index]
      x_filter.update_alpha(filter_time)
      a_filter.update_alpha(filter_time)
      v_filter.update_alpha(filter_time)
      if x_filter.initialized and x_lead <= x_filter.x:
        x_filter.x = x_lead
      else:
        x_filter.update(x_lead)
      x_lead = x_filter.x
      a_lead = a_filter.update(a_lead)
      v_lead = v_filter.update(v_lead)
    else:
      # Preserve the historical planner path outside the qualified comfort scene.
      self.lead_a_filter.update(a_lead)
      self.lead_v_filter.update(v_lead)
      a_lead = self.lead_a_filter.x
      v_lead = self.lead_v_filter.x
      self.duplicate_lead_x_filters[lead_index].initialized = False
      self.duplicate_lead_a_filters[lead_index].initialized = False
      self.duplicate_lead_v_filters[lead_index].initialized = False
    lead_xv = self.extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau, v_ego)
    return lead_xv

  @staticmethod
  def get_stable_follow_cruise_hysteresis(lead, v_ego, t_follow):
    if lead is None or not lead.status:
      return 0.0

    lead_radar = bool(getattr(lead, "radar", False))
    relative_speed = float(v_ego) - float(lead.vLead)
    actual_headway = None
    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > STABLE_FOLLOW_CRUISE_MAX_LEAD_BRAKE:
      return 0.0

    if lead_radar:
      if float(t_follow) <= 0.0 or float(v_ego) < STABLE_FOLLOW_CRUISE_MIN_SPEED:
        return 0.0
      if abs(relative_speed) > STABLE_FOLLOW_CRUISE_MAX_REL_SPEED:
        return 0.0

      actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
      min_headway = max(STABLE_FOLLOW_CRUISE_MIN_HEADWAY,
                        float(t_follow) - STABLE_FOLLOW_CRUISE_HEADWAY_BELOW_TARGET)
      max_headway = float(t_follow) + STABLE_FOLLOW_CRUISE_HEADWAY_ABOVE_TARGET
      if not (min_headway <= actual_headway <= max_headway):
        return 0.0
    elif not is_radarless_matched_follow_window(
      v_ego,
      lead.dRel,
      lead.vLead,
      t_follow,
      radar=lead_radar,
      lead_brake=lead_brake,
      lead_prob=float(getattr(lead, "modelProb", 0.0)),
      min_speed=STABLE_FOLLOW_CRUISE_MIN_SPEED,
    ):
      return 0.0
    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)

    hysteresis = max(STABLE_FOLLOW_CRUISE_HYSTERESIS_MIN,
                     STABLE_FOLLOW_CRUISE_HYSTERESIS_GAIN * float(v_ego))

    if relative_speed < 0.0:
      headway_margin = actual_headway - float(t_follow)
      if headway_margin <= STABLE_FOLLOW_CRUISE_PULLAWAY_MAX_HEADWAY_MARGIN:
        rel_speed_factor = float(np.clip((-relative_speed) / STABLE_FOLLOW_CRUISE_PULLAWAY_MAX_REL_SPEED, 0.0, 1.0))
        headway_factor = float(np.clip(
          (STABLE_FOLLOW_CRUISE_PULLAWAY_MAX_HEADWAY_MARGIN - headway_margin) /
          max(STABLE_FOLLOW_CRUISE_PULLAWAY_MAX_HEADWAY_MARGIN - STABLE_FOLLOW_CRUISE_PULLAWAY_MIN_HEADWAY_MARGIN, 1e-3),
          0.0, 1.0,
        ))
        hysteresis += STABLE_FOLLOW_CRUISE_PULLAWAY_HYSTERESIS_MAX * rel_speed_factor * headway_factor

    return hysteresis

  @staticmethod
  def leads_share_identical_radar_track(lead_one, lead_two):
    if lead_one is None or lead_two is None or not lead_one.status or not lead_two.status:
      return False
    if not (bool(getattr(lead_one, "radar", False)) and bool(getattr(lead_two, "radar", False))):
      return False
    track_one = int(getattr(lead_one, "radarTrackId", -1))
    track_two = int(getattr(lead_two, "radarTrackId", -1))
    return track_one >= 0 and track_one == track_two

  @staticmethod
  def leads_are_near_duplicates(lead_one, lead_two, v_ego, *, vision_min_speed=None):
    if lead_one is None or lead_two is None or not lead_one.status or not lead_two.status:
      return False
    if LongitudinalMpc.leads_share_identical_radar_track(lead_one, lead_two):
      if float(v_ego) < NEAR_DUPLICATE_IDENTICAL_RADAR_SOURCE_MIN_SPEED:
        return False
      return (
        abs(float(lead_one.dRel) - float(lead_two.dRel)) <= NEAR_DUPLICATE_LEAD_SOURCE_MAX_DREL_DIFF and
        abs(float(lead_one.vRel) - float(lead_two.vRel)) <= max(1.0, NEAR_DUPLICATE_LEAD_SOURCE_MAX_VREL_DIFF)
      )
    min_vision_speed = NEAR_DUPLICATE_LEAD_SOURCE_MIN_SPEED if vision_min_speed is None else float(vision_min_speed)
    if float(v_ego) < min_vision_speed:
      return False
    lead_one_radar = bool(getattr(lead_one, "radar", False))
    lead_two_radar = bool(getattr(lead_two, "radar", False))
    if lead_one_radar or lead_two_radar:
      return False
    if float(getattr(lead_one, "modelProb", 0.0)) < NEAR_DUPLICATE_LEAD_SOURCE_MIN_MODEL_PROB:
      return False
    if float(getattr(lead_two, "modelProb", 0.0)) < NEAR_DUPLICATE_LEAD_SOURCE_MIN_MODEL_PROB:
      return False
    if max(0.0, -float(getattr(lead_one, "aLeadK", 0.0))) > NEAR_DUPLICATE_LEAD_SOURCE_MAX_LEAD_BRAKE:
      return False
    if max(0.0, -float(getattr(lead_two, "aLeadK", 0.0))) > NEAR_DUPLICATE_LEAD_SOURCE_MAX_LEAD_BRAKE:
      return False

    return (
      abs(float(lead_one.dRel) - float(lead_two.dRel)) <= NEAR_DUPLICATE_LEAD_SOURCE_MAX_DREL_DIFF and
      abs(float(lead_one.vRel) - float(lead_two.vRel)) <= NEAR_DUPLICATE_LEAD_SOURCE_MAX_VREL_DIFF
    )

  def get_near_duplicate_lead_source_hysteresis(self, prev_source, lead_one, lead_two, v_ego):
    if prev_source not in ("lead0", "lead1"):
      return 0.0, 0.0
    if not self.leads_are_near_duplicates(lead_one, lead_two, v_ego):
      return 0.0, 0.0

    hysteresis = float(np.interp(
      float(v_ego),
      [NEAR_DUPLICATE_LEAD_SOURCE_MIN_SPEED, 35.0],
      [NEAR_DUPLICATE_LEAD_SOURCE_HYSTERESIS_MIN, NEAR_DUPLICATE_LEAD_SOURCE_HYSTERESIS_MAX],
    ))
    if prev_source == "lead0":
      return 0.0, hysteresis
    return hysteresis, 0.0

  def get_identical_radar_duplicate_source_hold(self, prev_source, lead_one, lead_two, lead_0_obstacle, lead_1_obstacle):
    if prev_source not in ("lead0", "lead1"):
      return None
    if not self.leads_share_identical_radar_track(lead_one, lead_two):
      return None
    if abs(float(lead_0_obstacle) - float(lead_1_obstacle)) > NEAR_DUPLICATE_IDENTICAL_RADAR_SOURCE_KEEP_MARGIN:
      return None
    return prev_source

  def get_identical_radar_duplicate_cruise_hold(self, prev_source, lead_one, lead_two,
                                                lead_0_obstacle, lead_1_obstacle, cruise_obstacle,
                                                v_ego, t_follow):
    if prev_source not in ("lead0", "lead1"):
      return None
    if float(v_ego) < IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MIN_SPEED:
      return None
    if not self.leads_share_identical_radar_track(lead_one, lead_two):
      return None
    if abs(float(lead_0_obstacle) - float(lead_1_obstacle)) > NEAR_DUPLICATE_IDENTICAL_RADAR_SOURCE_KEEP_MARGIN:
      return None

    prev_lead = lead_one if prev_source == "lead0" else lead_two
    if prev_lead is None or not prev_lead.status:
      return None

    actual_headway = float(prev_lead.dRel) / max(float(v_ego), 1e-3)
    if actual_headway > float(t_follow) + IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_HEADWAY_ABOVE_TARGET:
      return None

    lead_brake = max(0.0, -float(getattr(prev_lead, "aLeadK", 0.0)))
    if lead_brake > IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_LEAD_BRAKE:
      return None

    lead_delta = float(prev_lead.vLead) - float(v_ego)
    if lead_delta > IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_PULLAWAY_SPEED:
      return None

    prev_lead_obstacle = float(lead_0_obstacle if prev_source == "lead0" else lead_1_obstacle)
    cruise_advantage = prev_lead_obstacle - float(cruise_obstacle)
    if cruise_advantage > IDENTICAL_RADAR_DUPLICATE_CRUISE_HOLD_MAX_CRUISE_ADVANTAGE:
      return None

    return prev_source

  def get_vision_follow_cruise_hold(self, prev_source, lead_one, lead_two,
                                    lead_0_obstacle, lead_1_obstacle, cruise_obstacle,
                                    v_ego, t_follow, tracking_lead, *, early_follow=False):
    if not tracking_lead or prev_source not in ("lead0", "lead1"):
      return None

    prev_lead = lead_one if prev_source == "lead0" else lead_two
    if prev_lead is None or not prev_lead.status or bool(getattr(prev_lead, "radar", False)):
      return None
    if float(getattr(prev_lead, "modelProb", 0.0)) < VISION_FOLLOW_CRUISE_HOLD_MIN_MODEL_PROB:
      return None
    if early_follow:
      # Silverado admits a credible centered vision lead before it reaches the
      # normal matched-follow window. Hold that lead through the harmless
      # cruise/lead crossover, but never through a closing or braking lead.
      relative_speed = float(v_ego) - float(prev_lead.vLead)
      actual_headway = float(prev_lead.dRel) / max(float(v_ego), 1e-3)
      if (
        float(v_ego) < 18.0 or
        abs(relative_speed) > 2.5 or
        actual_headway < 0.95 or
        actual_headway > 2.35 or
        float(prev_lead.dRel) > 130.0 or
        abs(float(getattr(prev_lead, "yRel", 0.0))) > 1.2 or
        max(0.0, -float(getattr(prev_lead, "aLeadK", 0.0))) > 0.35 or
        float(getattr(prev_lead, "modelProb", 0.0)) < 0.95
      ):
        return None
    elif self.get_stable_follow_cruise_hysteresis(prev_lead, v_ego, t_follow) <= 0.0:
      return None

    prev_lead_obstacle = float(lead_0_obstacle if prev_source == "lead0" else lead_1_obstacle)
    cruise_advantage = prev_lead_obstacle - float(cruise_obstacle)
    if cruise_advantage > VISION_FOLLOW_CRUISE_HOLD_MAX_CRUISE_ADVANTAGE:
      return None

    return prev_source

  def get_identical_radar_duplicate_cruise_bias(self, lead_one, lead_two, v_ego, t_follow):
    if float(v_ego) < IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MIN_SPEED:
      return 0.0
    if not self.leads_share_identical_radar_track(lead_one, lead_two):
      return 0.0

    lead = lead_one if lead_one.status else lead_two
    if lead is None or not lead.status:
      return 0.0

    actual_headway = float(lead.dRel) / max(float(v_ego), 1e-3)
    headway_margin = actual_headway - float(t_follow)
    if headway_margin < IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MIN_HEADWAY_BELOW_TARGET:
      return 0.0
    if headway_margin > IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_HEADWAY_ABOVE_TARGET:
      return 0.0

    lead_brake = max(0.0, -float(getattr(lead, "aLeadK", 0.0)))
    if lead_brake > IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_LEAD_BRAKE:
      return 0.0

    lead_delta = float(lead.vLead) - float(v_ego)
    if lead_delta > IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_PULLAWAY_SPEED:
      return 0.0

    return float(np.interp(
      headway_margin,
      [IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MIN_HEADWAY_BELOW_TARGET, 0.0, IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX_HEADWAY_ABOVE_TARGET],
      [IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX, IDENTICAL_RADAR_DUPLICATE_CRUISE_BIAS_MAX * 0.85, 0.0],
    ))

  def set_accel_limits(self, min_a, max_a):
    # TODO this sets a max accel limit, but the minimum limit is only for cruise decel
    # needs refactor
    self.cruise_min_a = min_a
    self.max_a = max_a

  def update(self, radarstate, v_cruise, x, v, a, j, danger_factor, t_follow,
             personality=log.LongitudinalPersonality.standard, tracking_lead=True,
             optional_far_lead_comfort=True, smooth_duplicate_vision=False,
             stop_x=None, silverado_early_follow=False, modelV2=None,
             lead_obstacle_bias=(0.0, 0.0), tracked_lead_catchup_headway_margins=None,
             tracked_lead_catchup_bias_gain=None, tracked_lead_catchup_bias_cap=None,
             tracked_lead_catchup_speed_range=None, tracked_lead_catchup_fade_margins=None,
             tracked_lead_catchup_cruise_error_full=None):
    if self.honda_accord_11g_policy is not None:
      t_follow = get_T_FOLLOW(personality=personality)
      optional_far_lead_comfort = False
      smooth_duplicate_vision = False
      modelV2 = None
      lead_obstacle_bias = (0.0, 0.0)
      tracked_lead_catchup_headway_margins = None
      tracked_lead_catchup_bias_gain = None
      tracked_lead_catchup_bias_cap = None
      tracked_lead_catchup_speed_range = None
      tracked_lead_catchup_fade_margins = None
      tracked_lead_catchup_cruise_error_full = None

    v_ego = self.x0[1]
    lead_one = radarstate.leadOne
    lead_two = radarstate.leadTwo
    self.status = tracking_lead and (lead_one.status or lead_two.status)
    model_leads = getattr(modelV2, "leadsV3", ()) if modelV2 is not None else ()
    lead_xv_0 = self.process_lead(lead_one, tracking_lead, t_follow=t_follow, lead_index=0,
                                  smooth_duplicate_vision=smooth_duplicate_vision,
                                  model_lead=model_leads[0] if len(model_leads) > 0 else None)
    lead_xv_1 = self.process_lead(lead_two, tracking_lead, t_follow=t_follow, lead_index=1,
                                  smooth_duplicate_vision=smooth_duplicate_vision,
                                  model_lead=model_leads[1] if len(model_leads) > 1 else None)
    self.lead_xv_0 = lead_xv_0
    self.lead_xv_1 = lead_xv_1

    # To estimate a safe distance from a moving lead, we calculate how much stopping
    # distance that lead needs as a minimum. We can add that to the current distance
    # and then treat that as a stopped car/obstacle at this new distance.
    lead_0_obstacle = lead_xv_0[:,0] + get_stopped_equivalence_factor(lead_xv_0[:,1])
    lead_1_obstacle = lead_xv_1[:,0] + get_stopped_equivalence_factor(lead_xv_1[:,1])
    lead_0_obstacle -= float(lead_obstacle_bias[0])
    lead_1_obstacle -= float(lead_obstacle_bias[1])

    self.params[:,0] = ACCEL_MIN
    self.params[:,1] = ACCEL_MAX if self.honda_accord_11g_policy is not None else max(0.0, self.max_a)

    # Update in ACC mode or ACC/e2e blend
    if self.mode == 'acc':
      self.params[:,5] = LEAD_DANGER_FACTOR

      # Fake an obstacle for cruise, this ensures smooth acceleration to set speed
      # when the leads are no factor.
      cruise_min_a = (
        self.honda_accord_11g_policy["cruise_min_accel"]
        if self.honda_accord_11g_policy is not None else self.cruise_min_a
      )
      cruise_max_a = (
        self.honda_accord_11g_policy["cruise_max_accel"]
        if self.honda_accord_11g_policy is not None else self.max_a
      )
      v_lower = v_ego + (T_IDXS * cruise_min_a * 1.05)
      # TODO does this make sense when max_a is negative?
      v_upper = v_ego + (T_IDXS * cruise_max_a * 1.05)
      v_cruise_clipped = np.clip(v_cruise * np.ones(N+1),
                                 v_lower,
                                 v_upper)
      cruise_obstacle = np.cumsum(T_DIFFS * v_cruise_clipped) + get_safe_obstacle_distance(v_cruise_clipped, t_follow)
      prev_source = self.source
      if optional_far_lead_comfort:
        if prev_source == 'lead0':
          cruise_obstacle += self.get_stable_follow_cruise_hysteresis(lead_one, v_ego, t_follow)
        elif prev_source == 'lead1':
          cruise_obstacle += self.get_stable_follow_cruise_hysteresis(lead_two, v_ego, t_follow)
      crv_tracked_lead_tune = tracked_lead_catchup_bias_cap is not None
      if (optional_far_lead_comfort and tracking_lead and lead_one.status and
          (not crv_tracked_lead_tune or bool(getattr(lead_one, "radar", False)))):
        desired_gap = desired_follow_distance(v_ego, lead_one.vLead, t_follow)
        closing_speed = max(0.0, v_ego - lead_one.vLead)
        catchup_kwargs = {}
        if tracked_lead_catchup_headway_margins is not None:
          catchup_kwargs = {
            "min_headway_margin": tracked_lead_catchup_headway_margins[0],
            "full_headway_margin": tracked_lead_catchup_headway_margins[1],
          }
        if tracked_lead_catchup_bias_gain is not None:
          catchup_kwargs["bias_gain"] = tracked_lead_catchup_bias_gain
        if tracked_lead_catchup_bias_cap is not None:
          catchup_kwargs["bias_cap"] = tracked_lead_catchup_bias_cap
        if tracked_lead_catchup_speed_range is not None:
          catchup_kwargs["speed_range"] = tracked_lead_catchup_speed_range
        if tracked_lead_catchup_fade_margins is not None:
          catchup_kwargs["fade_margins"] = tracked_lead_catchup_fade_margins
        if tracked_lead_catchup_cruise_error_full is not None:
          catchup_kwargs["cruise_error_full"] = tracked_lead_catchup_cruise_error_full
        cruise_obstacle += get_tracked_lead_catchup_bias(
          v_ego,
          lead_one.dRel,
          desired_gap,
          closing_speed,
          v_cruise=v_cruise,
          y_rel=float(getattr(lead_one, "yRel", 0.0)),
          **catchup_kwargs,
        )
      if optional_far_lead_comfort:
        cruise_obstacle += self.get_identical_radar_duplicate_cruise_bias(lead_one, lead_two, v_ego, t_follow)
      if optional_far_lead_comfort:
        lead_0_bias, lead_1_bias = self.get_near_duplicate_lead_source_hysteresis(prev_source, lead_one, lead_two, v_ego)
        lead_0_obstacle = lead_0_obstacle + lead_0_bias
        lead_1_obstacle = lead_1_obstacle + lead_1_bias
      # A forced stop is a position constraint, not a speed one. Folded in here rather than
      # as a 4th column so the SOURCES[argmin] below keeps working. Lets the solver plan the
      # stop directly instead of chasing a descending speed ceiling with a persistent lag.
      if stop_x is not None:
        cruise_obstacle = np.minimum(cruise_obstacle, stop_x)
      x_obstacles = np.column_stack([lead_0_obstacle, lead_1_obstacle, cruise_obstacle])
      candidate_source = SOURCES[np.argmin(x_obstacles[0])]
      sticky_source = None
      if optional_far_lead_comfort:
        if candidate_source in ("lead0", "lead1"):
          sticky_source = self.get_identical_radar_duplicate_source_hold(
            prev_source,
            lead_one,
            lead_two,
            lead_0_obstacle[0],
            lead_1_obstacle[0],
          )
        elif candidate_source == "cruise":
          sticky_source = self.get_identical_radar_duplicate_cruise_hold(
            prev_source,
            lead_one,
            lead_two,
            lead_0_obstacle[0],
            lead_1_obstacle[0],
            cruise_obstacle[0],
            v_ego,
            t_follow,
          )
          if sticky_source is None:
            sticky_source = self.get_vision_follow_cruise_hold(
              prev_source,
              lead_one,
              lead_two,
              lead_0_obstacle[0],
              lead_1_obstacle[0],
              cruise_obstacle[0],
              v_ego,
              t_follow,
              tracking_lead,
              early_follow=silverado_early_follow,
            )
      self.source = sticky_source or candidate_source

      # These are not used in ACC mode
      x[:], v[:], a[:], j[:] = 0.0, 0.0, 0.0, 0.0

    elif self.mode == 'blended':
      self.params[:,5] = 1.0

      x_obstacles = np.column_stack([lead_0_obstacle,
                                     lead_1_obstacle])
      cruise_target = T_IDXS * np.clip(v_cruise, v_ego - 2.0, 1e3) + x[0]
      xforward = ((v[1:] + v[:-1]) / 2) * (T_IDXS[1:] - T_IDXS[:-1])
      x = np.cumsum(np.insert(xforward, 0, x[0]))

      if stop_x is not None:
        cruise_target = np.minimum(cruise_target, stop_x)
      x_and_cruise = np.column_stack([x, cruise_target])
      x = np.min(x_and_cruise, axis=1)

      self.source = 'e2e' if x_and_cruise[1,0] < x_and_cruise[1,1] else 'cruise'

    else:
      raise NotImplementedError(f'Planner mode {self.mode} not recognized in planner update')

    self.yref[:,1] = x
    self.yref[:,2] = v
    self.yref[:,3] = a
    self.yref[:,5] = j
    for i in range(N):
      self.solver.set(i, "yref", self.yref[i])
    self.solver.set(N, "yref", self.yref[N][:COST_E_DIM])

    self.params[:,2] = np.min(x_obstacles, axis=1)
    self.params[:,3] = np.copy(self.prev_a)
    self.params[:,4] = t_follow

    self.run()
    if (np.any(lead_xv_0[FCW_IDXS,0] - self.x_sol[FCW_IDXS,0] < CRASH_DISTANCE) and
            should_trigger_planner_fcw(lead_one, v_ego)):
      self.crash_cnt += 1
    else:
      self.crash_cnt = 0

    # Check if it got within lead comfort range
    # TODO This should be done cleaner
    if self.mode == 'blended':
      if any((lead_0_obstacle - get_safe_obstacle_distance(self.x_sol[:,1], t_follow))- self.x_sol[:,0] < 0.0):
        self.source = 'lead0'
      if any((lead_1_obstacle - get_safe_obstacle_distance(self.x_sol[:,1], t_follow))- self.x_sol[:,0] < 0.0) and \
         (lead_1_obstacle[0] - lead_0_obstacle[0]):
        self.source = 'lead1'

  def run(self):
    # t0 = time.monotonic()
    # reset = 0
    for i in range(N+1):
      self.solver.set(i, 'p', self.params[i])
    self.solver.constraints_set(0, "lbx", self.x0)
    self.solver.constraints_set(0, "ubx", self.x0)

    self.solution_status = self.solver.solve()
    self.solve_time = float(self.solver.get_stats('time_tot')[0])
    self.time_qp_solution = float(self.solver.get_stats('time_qp')[0])
    self.time_linearization = float(self.solver.get_stats('time_lin')[0])
    self.time_integrator = float(self.solver.get_stats('time_sim')[0])

    # qp_iter = self.solver.get_stats('statistics')[-1][-1] # SQP_RTI specific
    # print(f"long_mpc timings: tot {self.solve_time:.2e}, qp {self.time_qp_solution:.2e}, lin {self.time_linearization:.2e}, \
    # integrator {self.time_integrator:.2e}, qp_iter {qp_iter}")
    # res = self.solver.get_residuals()
    # print(f"long_mpc residuals: {res[0]:.2e}, {res[1]:.2e}, {res[2]:.2e}, {res[3]:.2e}")
    # self.solver.print_statistics()

    for i in range(N+1):
      self.x_sol[i] = self.solver.get(i, 'x')
    for i in range(N):
      self.u_sol[i] = self.solver.get(i, 'u')

    self.v_solution = self.x_sol[:,1]
    self.a_solution = self.x_sol[:,2]
    self.j_solution = self.u_sol[:,0]

    self.prev_a = np.interp(T_IDXS + self.dt, T_IDXS, self.a_solution)

    t = time.monotonic()
    if self.solution_status != 0:
      if t > self.last_cloudlog_t + 5.0:
        self.last_cloudlog_t = t
        cloudlog.warning(f"Long mpc reset, solution_status: {self.solution_status}")
      self.reset()
      # reset = 1
    # print(f"long_mpc timings: total internal {self.solve_time:.2e}, external: {(time.monotonic() - t0):.2e} qp {self.time_qp_solution:.2e}, \
    # lin {self.time_linearization:.2e} qp_iter {qp_iter}, reset {reset}")


if __name__ == "__main__":
  ocp = gen_long_ocp()
  AcadosOcpSolver.generate(ocp, json_file=JSON_FILE)
  # AcadosOcpSolver.build(ocp.code_export_directory, with_cython=True)
