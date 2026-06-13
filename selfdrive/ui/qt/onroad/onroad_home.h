#pragma once

#include "selfdrive/ui/qt/onroad/alerts.h"
#include "selfdrive/ui/qt/onroad/annotated_camera.h"

#include "starpilot/ui/qt/onroad/starpilot_onroad.h"

class OnroadWindow : public QWidget {
  Q_OBJECT

public:
  OnroadWindow(QWidget* parent = 0);

private:
  void paintEvent(QPaintEvent *event);
  OnroadAlerts *alerts;
  AnnotatedCameraWidget *nvg;
  QColor bg = bg_colors[STATUS_DISENGAGED];
  QHBoxLayout* split;

  void mousePressEvent(QMouseEvent* mouseEvent);
  void mouseReleaseEvent(QMouseEvent* mouseEvent);

  StarPilotAnnotatedCameraWidget *starpilot_nvg;
  StarPilotOnroadWindow *starpilot_onroad;

private slots:
  void offroadTransition(bool offroad);
  void updateState(const UIState &s, const StarPilotUIState &fs);
};
