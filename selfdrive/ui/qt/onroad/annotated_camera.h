#pragma once

#include <QVBoxLayout>
#include <memory>
#include "selfdrive/ui/qt/onroad/hud.h"
#include "selfdrive/ui/qt/onroad/buttons.h"
#include "selfdrive/ui/qt/onroad/driver_monitoring.h"
#include "selfdrive/ui/qt/onroad/model.h"
#include "selfdrive/ui/qt/widgets/cameraview.h"

#include "starpilot/ui/qt/onroad/starpilot_buttons.h"
#include "starpilot/ui/screenrecorder/screenrecorder.h"

class AnnotatedCameraWidget : public CameraWidget {
  Q_OBJECT

public:
  explicit AnnotatedCameraWidget(VisionStreamType type, QWidget* parent = 0);
  void updateState(const UIState &s, const StarPilotUIState &fs);
  bool handleHudPress(const QPoint &pos);
  bool handleHudRelease(const QPoint &pos);

  double fps;

  StarPilotAnnotatedCameraWidget *starpilot_nvg;

  StarPilotUIScene starpilot_scene;

  QJsonObject starpilot_toggles;

private:
  QVBoxLayout *main_layout;
  ExperimentalButton *experimental_btn;
  DriverMonitorRenderer dmon;
  HudRenderer hud;
  ModelRenderer model;
  std::unique_ptr<PubMaster> pm;

  int skip_frame_count = 0;
  bool wide_cam_requested = false;

  void paintEvent(QPaintEvent *event) override;

  DrivingPersonalityButton *personality_btn;
  ScreenRecorder *screen_recorder;

protected:
  void paintGL() override;
  void initializeGL() override;
  void showEvent(QShowEvent *event) override;
  mat4 calcFrameMatrix() override;

  double prev_draw_t = 0;
  FirstOrderFilter fps_filter;
};
