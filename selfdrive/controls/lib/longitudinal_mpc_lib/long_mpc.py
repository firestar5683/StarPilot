#!/usr/bin/env python3
import os
import time
import numpy as np
from cereal import log
from openpilot.common.numpy_fast import clip, interp
from openpilot.common.realtime import DT_MDL
from openpilot.common.swaglog import cloudlog
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.conversions import Conversions as CV
# WARNING: imports outside of constants will not trigger a rebuild
from openpilot.selfdrive.modeld.constants import index_function
from openpilot.selfdrive.car.interfaces import ACCEL_MIN

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

# DISTANCE ADAPTATION STRENGTH (How much penalties increase when close to lead)
# [City, Urban Hwy, Rural Hwy, High Speed]
DIST_ADAPTS = [0.04, 0.06, 0.06, 0.05]  # Balanced across speeds

# ===== END TUNING PARAMETERS =====

# Function to get parameter value based on current speed
def get_speed_based_param(speed_mph, param_array):
    """Get parameter value based on current speed using smooth interpolation"""
    return np.interp(speed_mph, SPEED_BREAKPOINTS, param_array)

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


# Fewer timestamps don't hurt performance and lead to
# much better convergence of the MPC with low iterations
N = 12
MAX_T = 10.0
T_IDXS_LST = [index_function(idx, max_val=MAX_T, max_idx=N) for idx in range(N+1)]

T_IDXS = np.array(T_IDXS_LST)
FCW_IDXS = T_IDXS < 5.0
T_DIFFS = np.diff(T_IDXS, prepend=[0.])
COMFORT_BRAKE = 2.5

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
  from openpilot.common.params import Params
  params = Params()
  stop_str = params.get("StopDistance", encoding="utf8")
  stop_distance = float(stop_str) if stop_str else 6.0
  return (v_ego**2) / (2 * COMFORT_BRAKE) + t_follow * v_ego + stop_distance

def desired_follow_distance(v_ego, v_lead, t_follow=None):
  if t_follow is None:
    t_follow = get_T_FOLLOW()
  return get_safe_obstacle_distance(v_ego, t_follow) - get_stopped_equivalence_factor(v_lead)


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
  def __init__(self, mode='acc', dt=DT_MDL):
    self.mode = mode
    self.dt = dt
    self.solver = AcadosOcpSolverCython(MODEL_NAME, ACADOS_SOLVER_TYPE, N)
    self.source = SOURCES[2]
    # Initialize smoothing filters with default time constants
    self.current_filter_time = LEAD_FILTER_TIME_LOW
    self.lead_a_filter = FirstOrderFilter(0.0, self.current_filter_time, self.dt)
    self.lead_v_filter = FirstOrderFilter(0.0, self.current_filter_time, self.dt)
    # Instance variables to avoid global modifications
    self.current_x_ego_cost = X_EGO_OBSTACLE_COSTS[0]
    self.current_j_ego_cost = J_EGO_COSTS[0]
    self.current_a_change_cost = A_CHANGE_COSTS[0]
    self.current_dist_adapt = DIST_ADAPTS[0]
    # Initialize acceleration limits to prevent AttributeError
    self.cruise_min_a = ACCEL_MIN
    self.max_a = 1.2  # Default max acceleration
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

  def set_weights(self, acceleration_jerk=1.0, danger_jerk=1.0, speed_jerk=1.0, prev_accel_constraint=True, personality=log.LongitudinalPersonality.standard, v_ego=0.0, lead_dist=50.0):
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
    if speed_mph < 35:
        self.current_filter_time = 0.0
    else:
        self.current_filter_time = interp(speed_mph, [35, 45], [0.0, LEAD_FILTER_TIME_HIGH])
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

  def set_cur_state(self, v, a):
    v_prev = self.x0[1]
    self.x0[1] = v
    self.x0[2] = a
    if abs(v_prev - v) > 2.:  # probably only helps if v < v_prev
      for i in range(N+1):
        self.solver.set(i, 'x', self.x0)

  @staticmethod
  def extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau, v_ego=0.0):
    speed_mph = v_ego * CV.MS_TO_MPH
    bp = [0, 20, 35]
    exp_weight = interp(speed_mph, bp, [1.0, 1.0, 0.0])  # Full exp at <20, blend to constant at 35

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

  def process_lead(self, lead, tracking_lead=True):
    v_ego = self.x0[1]
    if lead is not None and lead.status and tracking_lead:
      x_lead = lead.dRel
      v_lead = lead.vLead
      a_lead = lead.aLeadK
      a_lead_tau = lead.aLeadTau
    else:
      # Fake a fast lead car, so mpc can keep running in the same mode
      x_lead = 50.0
      v_lead = v_ego + 10.0
      a_lead = 0.0
      a_lead_tau = LEAD_ACCEL_TAU

    # MPC will not converge if immediate crash is expected
    # Clip lead distance to what is still possible to brake for
    min_x_lead = ((v_ego + v_lead)/2) * (v_ego - v_lead) / (-ACCEL_MIN * 2)
    x_lead = clip(x_lead, min_x_lead, 1e8)
    v_lead = clip(v_lead, 0.0, 1e8)
    a_lead = clip(a_lead, -10., 5.)
    # Apply smoothing filters with interp scaling
    self.lead_a_filter.update(a_lead)
    self.lead_v_filter.update(v_lead)
    a_lead = self.lead_a_filter.x
    v_lead = self.lead_v_filter.x
    lead_xv = self.extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau, v_ego)
    return lead_xv

  def set_accel_limits(self, min_a, max_a):
    # TODO this sets a max accel limit, but the minimum limit is only for cruise decel
    # needs refactor
    self.cruise_min_a = min_a
    self.max_a = max_a

  def update(self, lead_one, lead_two, v_cruise, x, v, a, j, t_follow, tracking_lead, personality=log.LongitudinalPersonality.standard):
    v_ego = self.x0[1]
    self.status = lead_one.status and tracking_lead or lead_two.status

    lead_xv_0 = self.process_lead(lead_one, tracking_lead)
    lead_xv_1 = self.process_lead(lead_two, v_ego)

    # To estimate a safe distance from a moving lead, we calculate how much stopping
    # distance that lead needs as a minimum. We can add that to the current distance
    # and then treat that as a stopped car/obstacle at this new distance.
    lead_0_obstacle = lead_xv_0[:,0] + get_stopped_equivalence_factor(lead_xv_0[:,1])
    lead_1_obstacle = lead_xv_1[:,0] + get_stopped_equivalence_factor(lead_xv_1[:,1])

    self.params[:,0] = ACCEL_MIN
    # negative accel constraint causes problems because negative speed is not allowed
    self.params[:,1] = max(0.0, self.max_a)

    # Update in ACC mode or ACC/e2e blend
    if self.mode == 'acc':
      self.params[:,5] = LEAD_DANGER_FACTOR

      # Fake an obstacle for cruise, this ensures smooth acceleration to set speed
      # when the leads are no factor.
      v_lower = v_ego + (T_IDXS * self.cruise_min_a * 1.05)
      # TODO does this make sense when max_a is negative?
      v_upper = v_ego + (T_IDXS * self.max_a * 1.05)
      v_cruise_clipped = np.clip(v_cruise * np.ones(N+1),
                                 v_lower,
                                 v_upper)
      cruise_obstacle = np.cumsum(T_DIFFS * v_cruise_clipped) + get_safe_obstacle_distance(v_cruise_clipped, t_follow)
      x_obstacles = np.column_stack([lead_0_obstacle, lead_1_obstacle, cruise_obstacle])
      self.source = SOURCES[np.argmin(x_obstacles[0])]

      # These are not used in ACC mode
      x[:], v[:], a[:], j[:] = 0.0, 0.0, 0.0, 0.0

    elif self.mode == 'blended':
      self.params[:,5] = 1.0

      x_obstacles = np.column_stack([lead_0_obstacle,
                                     lead_1_obstacle])
      cruise_target = T_IDXS * np.clip(v_cruise, v_ego - 2.0, 1e3) + x[0]
      xforward = ((v[1:] + v[:-1]) / 2) * (T_IDXS[1:] - T_IDXS[:-1])
      x = np.cumsum(np.insert(xforward, 0, x[0]))

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
    lead_probability = lead_one.modelProb
    if (np.any(lead_xv_0[FCW_IDXS,0] - self.x_sol[FCW_IDXS,0] < CRASH_DISTANCE) and lead_probability > 0.9):
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
