"""Output parsing for the v8–v16 model catalog; bundled parsing stays upstream."""

import numpy as np
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.selfdrive.modeld.parse_model_outputs import Parser as CurrentParser


class Parser(CurrentParser):
  def split_outputs(self, outs: dict[str, np.ndarray]) -> None:
    if 'lead' in outs:
      if outs['lead'].shape[1] == 2 * ModelConstants.LEAD_MHP_SELECTION * ModelConstants.LEAD_TRAJ_LEN * ModelConstants.LEAD_WIDTH:
        self.parse_mdn('lead', outs, in_N=0, out_N=0,
                       out_shape=(ModelConstants.LEAD_MHP_SELECTION, ModelConstants.LEAD_TRAJ_LEN, ModelConstants.LEAD_WIDTH))
      else:
        self.parse_mdn('lead', outs, in_N=ModelConstants.LEAD_MHP_N, out_N=ModelConstants.LEAD_MHP_SELECTION,
                       out_shape=(ModelConstants.LEAD_TRAJ_LEN, ModelConstants.LEAD_WIDTH))
    if 'plan' in outs:
      plan_mhp = outs['plan'].shape[1] != 2 * ModelConstants.IDX_N * ModelConstants.PLAN_WIDTH
      plan_in_N, plan_out_N = (ModelConstants.PLAN_MHP_N, ModelConstants.PLAN_MHP_SELECTION) if plan_mhp else (0, 0)
      self.parse_mdn('plan', outs, in_N=plan_in_N, out_N=plan_out_N,
                     out_shape=(ModelConstants.IDX_N, ModelConstants.PLAN_WIDTH))
      if 'planplus' in outs:
        self.parse_mdn('planplus', outs, in_N=plan_in_N, out_N=plan_out_N, out_shape=(ModelConstants.IDX_N, ModelConstants.PLAN_WIDTH))
    elif 'planplus' in outs:
      planplus_mhp = outs['planplus'].shape[1] != 2 * ModelConstants.IDX_N * ModelConstants.PLAN_WIDTH
      planplus_in_N, planplus_out_N = (ModelConstants.PLAN_MHP_N, ModelConstants.PLAN_MHP_SELECTION) if planplus_mhp else (0, 0)
      self.parse_mdn('planplus', outs, in_N=planplus_in_N, out_N=planplus_out_N, out_shape=(ModelConstants.IDX_N, ModelConstants.PLAN_WIDTH))
    if 'lane_lines' in outs:
      self.parse_mdn('lane_lines', outs, in_N=0, out_N=0,
                     out_shape=(ModelConstants.NUM_LANE_LINES, ModelConstants.IDX_N, ModelConstants.LANE_LINES_WIDTH))
    if 'road_edges' in outs:
      self.parse_mdn('road_edges', outs, in_N=0, out_N=0,
                     out_shape=(ModelConstants.NUM_ROAD_EDGES, ModelConstants.IDX_N, ModelConstants.LANE_LINES_WIDTH))
    if 'sim_pose' in outs:
      self.parse_mdn('sim_pose', outs, in_N=0, out_N=0, out_shape=(ModelConstants.POSE_WIDTH,))
    if 'lane_lines_prob' in outs:
      self.parse_binary_crossentropy('lane_lines_prob', outs)
    if 'lead_prob' in outs:
      self.parse_binary_crossentropy('lead_prob', outs)

  def parse_off_policy_outputs(self, outs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    self.split_outputs(outs)
    if 'desire_state' in outs:
      self.parse_categorical_crossentropy('desire_state', outs, out_shape=(ModelConstants.DESIRE_PRED_WIDTH,))
    return outs

  def parse_vision_outputs(self, outs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    self.parse_mdn('pose', outs, in_N=0, out_N=0, out_shape=(ModelConstants.POSE_WIDTH,))
    self.parse_mdn('wide_from_device_euler', outs, in_N=0, out_N=0, out_shape=(ModelConstants.WIDE_FROM_DEVICE_WIDTH,))
    self.parse_mdn('road_transform', outs, in_N=0, out_N=0, out_shape=(ModelConstants.POSE_WIDTH,))
    self.split_outputs(outs)
    self.parse_categorical_crossentropy('desire_pred', outs, out_shape=(ModelConstants.DESIRE_PRED_LEN, ModelConstants.DESIRE_PRED_WIDTH))
    self.parse_binary_crossentropy('meta', outs)
    return outs

  def parse_policy_outputs(self, outs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    self.split_outputs(outs)
    if 'action' in outs:
      self.parse_mdn('action', outs, in_N=0, out_N=0, out_shape=(ModelConstants.ACTION_WIDTH,))
    if 'lat_planner_solution' in outs:
      self.parse_mdn('lat_planner_solution', outs, in_N=0, out_N=0, out_shape=(ModelConstants.IDX_N, ModelConstants.LAT_PLANNER_SOLUTION_WIDTH))
    if 'desired_curvature' in outs:
      self.parse_mdn('desired_curvature', outs, in_N=0, out_N=0, out_shape=(ModelConstants.DESIRED_CURV_WIDTH,))
    if 'desire_state' in outs:
      self.parse_categorical_crossentropy('desire_state', outs, out_shape=(ModelConstants.DESIRE_PRED_WIDTH,))
    return outs

  def parse_outputs(self, outs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    # Combined supercombo outputs contain both vision and policy slices in the
    # same dictionary. Parse shared MDN outputs once; the split runtime keeps
    # using parse_vision_outputs/parse_policy_outputs independently.
    self.parse_mdn('pose', outs, in_N=0, out_N=0, out_shape=(ModelConstants.POSE_WIDTH,))
    self.parse_mdn('wide_from_device_euler', outs, in_N=0, out_N=0, out_shape=(ModelConstants.WIDE_FROM_DEVICE_WIDTH,))
    self.parse_mdn('road_transform', outs, in_N=0, out_N=0, out_shape=(ModelConstants.POSE_WIDTH,))
    self.split_outputs(outs)
    self.parse_categorical_crossentropy('desire_pred', outs, out_shape=(ModelConstants.DESIRE_PRED_LEN, ModelConstants.DESIRE_PRED_WIDTH))
    self.parse_binary_crossentropy('meta', outs)
    if 'action' in outs:
      self.parse_mdn('action', outs, in_N=0, out_N=0, out_shape=(ModelConstants.ACTION_WIDTH,))
    if 'lat_planner_solution' in outs:
      self.parse_mdn('lat_planner_solution', outs, in_N=0, out_N=0,
                     out_shape=(ModelConstants.IDX_N, ModelConstants.LAT_PLANNER_SOLUTION_WIDTH))
    if 'desired_curvature' in outs:
      self.parse_mdn('desired_curvature', outs, in_N=0, out_N=0, out_shape=(ModelConstants.DESIRED_CURV_WIDTH,))
    if 'desire_state' in outs:
      self.parse_categorical_crossentropy('desire_state', outs, out_shape=(ModelConstants.DESIRE_PRED_WIDTH,))
    return outs
