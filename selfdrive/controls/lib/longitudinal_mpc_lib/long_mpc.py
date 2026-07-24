#!/usr/bin/env python3
import os
import time

import numpy as np
from casadi import SX, vertcat
from cereal import log

try:
  from opendbc.car.interfaces import ACCEL_MIN, ACCEL_MAX
except Exception:
  # Generated-code builds run before every opendbc extension is available.
  ACCEL_MIN = -3.5
  ACCEL_MAX = 2.0

from openpilot.common.realtime import DT_MDL
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.modeld.constants import index_function

if __name__ == "__main__":
  from openpilot.third_party.acados.acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver
else:
  from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.c_generated_code.acados_ocp_solver_pyx import AcadosOcpSolverCython


MODEL_NAME = "long"
LONG_MPC_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(LONG_MPC_DIR, "c_generated_code")
JSON_FILE = os.path.join(LONG_MPC_DIR, "acados_ocp_long.json")

SOURCES = ("lead0", "lead1", "cruise")

X_DIM = 3
U_DIM = 1
PARAM_DIM = 6
COST_E_DIM = 5
COST_DIM = COST_E_DIM + 1
CONSTR_DIM = 4

X_EGO_OBSTACLE_COST = 3.0
J_EGO_COST = 5.0
A_CHANGE_COST = 200.0
DANGER_ZONE_COST = 100.0
LEAD_DANGER_FACTOR = 0.75
LIMIT_COST = 1e6
CRASH_DISTANCE = 0.25
ACADOS_SOLVER_TYPE = "SQP_RTI"

N = 12
MAX_T = 10.0
T_IDXS = np.array([index_function(i, max_val=MAX_T, max_idx=N) for i in range(N + 1)])
T_DIFFS = np.diff(T_IDXS, prepend=[0.0])
FCW_IDXS = T_IDXS < 5.0

COMFORT_BRAKE = 2.5
STOP_DISTANCE = 6.0
CRUISE_MIN_ACCEL = -1.2
CRUISE_MAX_ACCEL = 1.6
LEAD_ACCEL_TAU = 1.5
LEAD_FILTER_TAU = 0.45
LEAD_FILTER_RESET_DISTANCE = 8.0

FCW_MIN_MODEL_PROB = 0.9
FCW_MIN_CLOSING_SPEED = 0.5
FCW_MAX_TTC = 4.0


def _personality_value(aggressive, standard, relaxed, personality):
  return {
    log.LongitudinalPersonality.aggressive: aggressive,
    log.LongitudinalPersonality.standard: standard,
    log.LongitudinalPersonality.relaxed: relaxed,
  }[personality]


def get_jerk_factor(aggressive_accel=0.5, aggressive_danger=0.5, aggressive_speed=0.5,
                    standard_accel=1.0, standard_danger=1.0, standard_speed=1.0,
                    relaxed_accel=1.0, relaxed_danger=1.0, relaxed_speed=1.0,
                    custom_personalities=False,
                    personality=log.LongitudinalPersonality.standard):
  if not custom_personalities:
    factor = 0.5 if personality == log.LongitudinalPersonality.aggressive else 1.0
    return factor, factor, factor

  return (
    _personality_value(aggressive_accel, standard_accel, relaxed_accel, personality),
    _personality_value(aggressive_danger, standard_danger, relaxed_danger, personality),
    _personality_value(aggressive_speed, standard_speed, relaxed_speed, personality),
  )


def get_T_FOLLOW(aggressive_follow=1.25, standard_follow=1.45, relaxed_follow=1.75,
                 custom_personalities=False,
                 personality=log.LongitudinalPersonality.standard):
  if custom_personalities:
    return _personality_value(aggressive_follow, standard_follow, relaxed_follow, personality)
  return _personality_value(1.25, 1.45, 1.75, personality)


def get_stopped_equivalence_factor(v_lead):
  return (v_lead ** 2) / (2.0 * COMFORT_BRAKE)


def get_safe_obstacle_distance(v_ego, t_follow):
  return (v_ego ** 2) / (2.0 * COMFORT_BRAKE) + t_follow * v_ego + STOP_DISTANCE


def desired_follow_distance(v_ego, v_lead, t_follow=None):
  t_follow = get_T_FOLLOW() if t_follow is None else t_follow
  return get_safe_obstacle_distance(v_ego, t_follow) - get_stopped_equivalence_factor(v_lead)


def should_trigger_planner_fcw(lead, v_ego):
  if lead is None or not bool(getattr(lead, "status", False)):
    return False
  if float(getattr(lead, "modelProb", 0.0)) <= FCW_MIN_MODEL_PROB:
    return False

  closing_speed = max(0.0, float(v_ego) - float(getattr(lead, "vLead", 0.0)))
  ttc = max(0.0, float(getattr(lead, "dRel", 0.0))) / max(closing_speed, 1e-3)
  return closing_speed >= FCW_MIN_CLOSING_SPEED and ttc < FCW_MAX_TTC


def gen_long_model():
  model = AcadosModel()
  model.name = MODEL_NAME

  x_ego = SX.sym("x_ego")
  v_ego = SX.sym("v_ego")
  a_ego = SX.sym("a_ego")
  model.x = vertcat(x_ego, v_ego, a_ego)

  j_ego = SX.sym("j_ego")
  model.u = vertcat(j_ego)

  x_ego_dot = SX.sym("x_ego_dot")
  v_ego_dot = SX.sym("v_ego_dot")
  a_ego_dot = SX.sym("a_ego_dot")
  model.xdot = vertcat(x_ego_dot, v_ego_dot, a_ego_dot)

  a_min = SX.sym("a_min")
  a_max = SX.sym("a_max")
  x_obstacle = SX.sym("x_obstacle")
  prev_a = SX.sym("prev_a")
  lead_t_follow = SX.sym("lead_t_follow")
  lead_danger_factor = SX.sym("lead_danger_factor")
  model.p = vertcat(a_min, a_max, x_obstacle, prev_a, lead_t_follow, lead_danger_factor)

  dynamics = vertcat(v_ego, a_ego, j_ego)
  model.f_impl_expr = model.xdot - dynamics
  model.f_expl_expr = dynamics
  return model


def gen_long_ocp():
  ocp = AcadosOcp()
  ocp.model = gen_long_model()
  ocp.dims.N = N

  ocp.cost.cost_type = "NONLINEAR_LS"
  ocp.cost.cost_type_e = "NONLINEAR_LS"
  ocp.cost.W = np.zeros((COST_DIM, COST_DIM))
  ocp.cost.W_e = np.zeros((COST_E_DIM, COST_E_DIM))

  x_ego, v_ego, a_ego = ocp.model.x[0], ocp.model.x[1], ocp.model.x[2]
  j_ego = ocp.model.u[0]
  a_min = ocp.model.p[0]
  a_max = ocp.model.p[1]
  x_obstacle = ocp.model.p[2]
  prev_a = ocp.model.p[3]
  t_follow = ocp.model.p[4]
  danger_factor = ocp.model.p[5]

  desired_distance = get_safe_obstacle_distance(v_ego, t_follow)
  costs = [
    ((x_obstacle - x_ego) - desired_distance) / (v_ego + 10.0),
    x_ego,
    v_ego,
    a_ego,
    a_ego - prev_a,
    j_ego,
  ]
  ocp.model.cost_y_expr = vertcat(*costs)
  ocp.model.cost_y_expr_e = vertcat(*costs[:-1])
  ocp.cost.yref = np.zeros(COST_DIM)
  ocp.cost.yref_e = np.zeros(COST_E_DIM)

  ocp.model.con_h_expr = vertcat(
    v_ego,
    a_ego - a_min,
    a_max - a_ego,
    ((x_obstacle - x_ego) - danger_factor * desired_distance) / (v_ego + 10.0),
  )

  ocp.constraints.x0 = np.zeros(X_DIM)
  ocp.parameter_values = np.array([
    CRUISE_MIN_ACCEL,
    CRUISE_MAX_ACCEL,
    0.0,
    0.0,
    get_T_FOLLOW(),
    LEAD_DANGER_FACTOR,
  ])

  zero_constraints = np.zeros(CONSTR_DIM)
  ocp.cost.zl = zero_constraints
  ocp.cost.Zl = zero_constraints
  ocp.cost.Zu = zero_constraints
  ocp.cost.zu = zero_constraints
  ocp.constraints.lh = zero_constraints
  ocp.constraints.uh = 1e4 * np.ones(CONSTR_DIM)
  ocp.constraints.idxsh = np.arange(CONSTR_DIM)

  ocp.solver_options.qp_solver = "PARTIAL_CONDENSING_HPIPM"
  ocp.solver_options.hessian_approx = "GAUSS_NEWTON"
  ocp.solver_options.integrator_type = "ERK"
  ocp.solver_options.nlp_solver_type = ACADOS_SOLVER_TYPE
  ocp.solver_options.qp_solver_cond_N = 1
  ocp.solver_options.qp_solver_iter_max = 10
  ocp.solver_options.qp_tol = 1e-3
  ocp.solver_options.tf = T_IDXS[-1]
  ocp.solver_options.shooting_nodes = T_IDXS
  ocp.code_export_directory = EXPORT_DIR
  return ocp


class LongitudinalMpc:
  def __init__(self, mode="acc", dt=DT_MDL):
    self.mode = mode
    self.dt = dt
    self.solver = AcadosOcpSolverCython(MODEL_NAME, ACADOS_SOLVER_TYPE, N)
    self.cruise_min_a = CRUISE_MIN_ACCEL
    self.max_a = CRUISE_MAX_ACCEL
    self.lead_filter_tau = LEAD_FILTER_TAU
    self.source = "cruise"
    self._lead_filter_state = [None, None]
    self.reset()

  def reset(self):
    self.solver.reset()
    self.x_sol = np.zeros((N + 1, X_DIM))
    self.u_sol = np.zeros((N, U_DIM))
    self.v_solution = np.zeros(N + 1)
    self.a_solution = np.zeros(N + 1)
    self.j_solution = np.zeros(N)
    self.prev_a = np.zeros(N + 1)
    self.yref = np.zeros((N + 1, COST_DIM))
    self.params = np.zeros((N + 1, PARAM_DIM))
    self.x0 = np.zeros(X_DIM)
    self.crash_cnt = 0
    self.solution_status = 0
    self.solve_time = 0.0
    self.last_cloudlog_t = 0.0
    self._lead_filter_state = [None, None]

    for i in range(N):
      self.solver.cost_set(i, "yref", self.yref[i])
    self.solver.cost_set(N, "yref", self.yref[N][:COST_E_DIM])
    for i in range(N + 1):
      self.solver.set(i, "x", np.zeros(X_DIM))
    self.set_weights()

  def set_cost_weights(self, cost_weights, constraint_cost_weights):
    weights = np.asfortranarray(np.diag(cost_weights))
    for i in range(N):
      weights[4, 4] = cost_weights[4] * np.interp(T_IDXS[i], [0.0, 1.0, 2.0], [1.0, 1.0, 0.0])
      self.solver.cost_set(i, "W", weights)
    self.solver.cost_set(N, "W", np.copy(weights[:COST_E_DIM, :COST_E_DIM]))

    constraints = np.asarray(constraint_cost_weights)
    for i in range(N):
      self.solver.cost_set(i, "Zl", constraints)

  def set_weights(self, acceleration_jerk=1.0, danger_jerk=1.0, speed_jerk=1.0,
                  prev_accel_constraint=True, **_):
    accel_change_cost = acceleration_jerk * A_CHANGE_COST if prev_accel_constraint else 0.0
    costs = [X_EGO_OBSTACLE_COST, 0.0, 0.0, 0.0, accel_change_cost, speed_jerk * J_EGO_COST]
    constraints = [LIMIT_COST, LIMIT_COST, LIMIT_COST, danger_jerk * DANGER_ZONE_COST]
    self.set_cost_weights(costs, constraints)

  def set_cur_state(self, v_ego, a_ego):
    previous_v = self.x0[1]
    self.x0[1] = v_ego
    self.x0[2] = a_ego
    if abs(previous_v - v_ego) > 2.0:
      for i in range(N + 1):
        self.solver.set(i, "x", self.x0)

  def set_accel_limits(self, min_a, max_a):
    self.cruise_min_a = float(min_a)
    self.max_a = float(max_a)

  @staticmethod
  def extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau):
    a_traj = a_lead * np.exp(-a_lead_tau * (T_IDXS ** 2) / 2.0)
    v_traj = np.clip(v_lead + np.cumsum(T_DIFFS * a_traj), 0.0, 1e8)
    x_traj = x_lead + np.cumsum(T_DIFFS * v_traj)
    return np.column_stack((x_traj, v_traj))

  def _filter_lead_motion(self, index, lead):
    raw_distance = float(lead.dRel)
    raw_velocity = float(lead.vLead)
    raw_accel = float(lead.aLeadK)
    state = self._lead_filter_state[index]

    reset = state is None or abs(raw_distance - state[2]) > LEAD_FILTER_RESET_DISTANCE
    if reset:
      filtered_velocity = raw_velocity
      filtered_accel = raw_accel
    else:
      alpha = self.dt / (self.lead_filter_tau + self.dt)
      filtered_velocity = state[0] + alpha * (raw_velocity - state[0])
      filtered_accel = state[1] + alpha * (raw_accel - state[1])

    self._lead_filter_state[index] = (filtered_velocity, filtered_accel, raw_distance)
    return filtered_velocity, filtered_accel

  def process_lead(self, lead, index):
    v_ego = self.x0[1]
    present = lead is not None and bool(getattr(lead, "status", False))
    if present:
      x_lead = float(lead.dRel)
      v_lead, a_lead = self._filter_lead_motion(index, lead)
      a_lead_tau = max(float(getattr(lead, "aLeadTau", LEAD_ACCEL_TAU)), 0.1)
    else:
      self._lead_filter_state[index] = None
      x_lead = 50.0
      v_lead = v_ego + 10.0
      a_lead = 0.0
      a_lead_tau = LEAD_ACCEL_TAU

    min_x_lead = ((v_ego + v_lead) / 2.0) * (v_ego - v_lead) / (-ACCEL_MIN * 2.0)
    x_lead = float(np.clip(x_lead, min_x_lead, 1e8))
    v_lead = float(np.clip(v_lead, 0.0, 1e8))
    a_lead = float(np.clip(a_lead, -10.0, 5.0))
    return self.extrapolate_lead(x_lead, v_lead, a_lead, a_lead_tau)

  def update(self, radarstate, v_cruise, x=None, v=None, a=None, j=None,
             danger_factor=LEAD_DANGER_FACTOR, t_follow=None,
             personality=log.LongitudinalPersonality.standard, **_):
    t_follow = get_T_FOLLOW(personality=personality) if t_follow is None else float(t_follow)
    v_ego = self.x0[1]

    lead_trajectories = [
      self.process_lead(radarstate.leadOne, 0),
      self.process_lead(radarstate.leadTwo, 1),
    ]
    lead_obstacles = [
      trajectory[:, 0] + get_stopped_equivalence_factor(trajectory[:, 1])
      for trajectory in lead_trajectories
    ]

    v_lower = v_ego + T_IDXS * self.cruise_min_a * 1.05
    v_upper = v_ego + T_IDXS * self.max_a * 1.05
    v_cruise_clipped = np.clip(np.full(N + 1, v_cruise), v_lower, v_upper)
    cruise_obstacle = np.cumsum(T_DIFFS * v_cruise_clipped) + get_safe_obstacle_distance(v_cruise_clipped, t_follow)

    obstacles = np.column_stack((*lead_obstacles, cruise_obstacle))
    self.source = SOURCES[int(np.argmin(obstacles[0]))]

    self.yref.fill(0.0)
    for i in range(N):
      self.solver.set(i, "yref", self.yref[i])
    self.solver.set(N, "yref", self.yref[N][:COST_E_DIM])

    self.params[:, 0] = self.cruise_min_a
    self.params[:, 1] = max(0.0, self.max_a)
    self.params[:, 2] = np.min(obstacles, axis=1)
    self.params[:, 3] = self.prev_a
    self.params[:, 4] = t_follow
    self.params[:, 5] = float(danger_factor)

    self.run()

    crash_risk = False
    for lead, trajectory in zip((radarstate.leadOne, radarstate.leadTwo), lead_trajectories, strict=True):
      crash_risk |= bool(
        should_trigger_planner_fcw(lead, v_ego) and
        np.any(trajectory[FCW_IDXS, 0] - self.x_sol[FCW_IDXS, 0] < CRASH_DISTANCE)
      )
    self.crash_cnt = self.crash_cnt + 1 if crash_risk else 0

  def run(self):
    for i in range(N + 1):
      self.solver.set(i, "p", self.params[i])
    self.solver.constraints_set(0, "lbx", self.x0)
    self.solver.constraints_set(0, "ubx", self.x0)

    self.solution_status = self.solver.solve()
    self.solve_time = float(self.solver.get_stats("time_tot")[0])

    for i in range(N + 1):
      self.x_sol[i] = self.solver.get(i, "x")
    for i in range(N):
      self.u_sol[i] = self.solver.get(i, "u")

    self.v_solution = self.x_sol[:, 1]
    self.a_solution = self.x_sol[:, 2]
    self.j_solution = self.u_sol[:, 0]
    self.prev_a = np.interp(T_IDXS + self.dt, T_IDXS, self.a_solution)

    if self.solution_status != 0:
      now = time.monotonic()
      if now > self.last_cloudlog_t + 5.0:
        self.last_cloudlog_t = now
        cloudlog.warning(f"Long MPC reset, solution_status: {self.solution_status}")
      self.reset()


if __name__ == "__main__":
  ocp = gen_long_ocp()
  AcadosOcpSolver.generate(ocp, json_file=JSON_FILE)
