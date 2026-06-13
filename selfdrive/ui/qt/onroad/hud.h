#pragma once

#include <QHash>
#include <QElapsedTimer>
#include <QJsonObject>
#include <QPainter>
#include <QPixmap>
#include "selfdrive/ui/ui.h"

#include "starpilot/ui/qt/onroad/starpilot_annotated_camera.h"

class HudRenderer : public QObject {
  Q_OBJECT

public:
  HudRenderer();
  void updateState(const UIState &s);
  void draw(QPainter &p, const QRect &surface_rect);
  bool handleNavigationPress(const QPoint &pos);
  bool handleNavigationRelease(const QPoint &pos);

  StarPilotAnnotatedCameraWidget *starpilot_nvg;

  QJsonObject starpilot_toggles;

private:
  void drawSetSpeed(QPainter &p, const QRect &surface_rect);
  void drawCurrentSpeed(QPainter &p, const QRect &surface_rect);
  void drawNavigationCard(QPainter &p, const QRect &surface_rect);
  void drawText(QPainter &p, int x, int y, const QString &text, int alpha = 255);
  QStringList wrapNavigationText(int max_width, int font_size, const QString &text) const;
  QString formatNavDistance(float distance_m) const;
  QString navigationIconFilename(const QString &maneuver_type, const QString &modifier) const;
  QPixmap getNavigationIcon(const QString &maneuver_type, const QString &modifier, int size);
  void cancelNavigation();

  float speed = 0;
  float set_speed = 0;
  bool is_cruise_set = false;
  bool is_cruise_available = true;
  bool is_metric = false;
  bool v_ego_cluster_seen = false;
  bool navigation_enabled = false;
  bool navigation_valid = false;
  bool navigation_has_next = false;
  bool navigation_collapsed = false;
  int status = STATUS_DISENGAGED;
  QString nav_distance;
  QString nav_primary_text;
  QString nav_secondary_text;
  QString nav_maneuver_type;
  QString nav_modifier;
  QString nav_next_maneuver_type;
  QString nav_next_modifier;
  QRect nav_hit_rect;
  QHash<QString, QPixmap> nav_icon_cache;
  QElapsedTimer nav_press_timer;
  bool nav_press_active = false;
  Params params;
  Params params_memory{"", true};
};
