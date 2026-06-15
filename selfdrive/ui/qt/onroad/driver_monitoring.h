#pragma once

#include <vector>
#include <QPainter>
#include "selfdrive/ui/ui.h"

#include "starpilot/ui/qt/onroad/starpilot_annotated_camera.h"

class DriverMonitorRenderer {
public:
  DriverMonitorRenderer();
  void updateState(const UIState &s);
  void draw(QPainter &painter, const QRect &surface_rect);

  StarPilotAnnotatedCameraWidget *starpilot_nvg;

  int onroad_controls_width = 0;

  QJsonObject starpilot_toggles;

private:
  float driver_pose_vals[3] = {};
  float driver_pose_diff[3] = {};
  float driver_pose_sins[3] = {};
  float driver_pose_coss[3] = {};
  bool is_visible = false;
  bool is_active = false;
  bool is_rhd = false;
  float dm_fade_state = 1.0;
  QPixmap dm_img;
  std::vector<vec3> face_kpts_draw;
};
