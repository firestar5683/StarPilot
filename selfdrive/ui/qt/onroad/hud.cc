#include "selfdrive/ui/qt/onroad/hud.h"

#include <algorithm>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <cmath>

#include "selfdrive/ui/qt/util.h"

constexpr int SET_SPEED_NA = 255;
constexpr int NAV_CANCEL_HOLD_MS = 650;

HudRenderer::HudRenderer() {}

bool HudRenderer::handleNavigationPress(const QPoint &pos) {
  if (!navigation_valid || !nav_hit_rect.contains(pos)) {
    return false;
  }

  nav_press_active = true;
  nav_press_timer.restart();
  return true;
}

bool HudRenderer::handleNavigationRelease(const QPoint &pos) {
  if (!nav_press_active) {
    return false;
  }

  nav_press_active = false;
  if (!nav_hit_rect.contains(pos)) {
    return true;
  }

  if (nav_press_timer.isValid() && nav_press_timer.elapsed() >= NAV_CANCEL_HOLD_MS) {
    cancelNavigation();
  } else {
    params_memory.putBool("NavInstructionCollapsed", !navigation_collapsed);
  }
  return true;
}

void HudRenderer::cancelNavigation() {
  params.remove("NavDestination");
  params_memory.remove("NavInstructionState");
  params_memory.remove("NavInstructionCollapsed");
  navigation_valid = false;
  navigation_collapsed = false;
  nav_hit_rect = QRect();
  nav_primary_text.clear();
  nav_secondary_text.clear();
  nav_distance.clear();
  nav_maneuver_type.clear();
  nav_modifier.clear();
  nav_next_maneuver_type.clear();
  nav_next_modifier.clear();
}

void HudRenderer::updateState(const UIState &s) {
  is_metric = s.scene.is_metric;
  status = s.status;

  const SubMaster &sm = *(s.sm);
  if (sm.rcv_frame("carState") < s.scene.started_frame) {
    is_cruise_set = false;
    set_speed = SET_SPEED_NA;
    speed = 0.0;
    return;
  }

  const auto &controls_state = sm["controlsState"].getControlsState();
  const auto &car_state = sm["carState"].getCarState();

  // Handle older routes where vCruiseCluster is not set
  set_speed = car_state.getVCruiseCluster() == 0.0 ? controls_state.getVCruiseDEPRECATED() : car_state.getVCruiseCluster();
  is_cruise_set = set_speed > 0 && set_speed != SET_SPEED_NA;
  is_cruise_available = set_speed != -1;

  if (is_cruise_set && starpilot_toggles.value("set_speed_offset").toDouble() > 0) {
    set_speed += starpilot_toggles.value("set_speed_offset").toDouble();
  }

  if (is_cruise_set && !is_metric) {
    set_speed *= KM_TO_MILE;
  }

  // Handle older routes where vEgoCluster is not set
  v_ego_cluster_seen = v_ego_cluster_seen || car_state.getVEgoCluster() != 0.0;
  float v_ego = v_ego_cluster_seen && !starpilot_toggles.value("use_wheel_speed").toBool() ? car_state.getVEgoCluster() : car_state.getVEgo();
  speed = std::max<float>(0.0f, v_ego * (is_metric ? MS_TO_KPH : MS_TO_MPH));

  navigation_enabled = params.getBool("NavigationUI");
  navigation_valid = false;
  navigation_has_next = false;
  navigation_collapsed = false;
  nav_hit_rect = QRect();
  nav_primary_text.clear();
  nav_secondary_text.clear();
  nav_distance.clear();
  nav_maneuver_type.clear();
  nav_modifier.clear();
  nav_next_maneuver_type.clear();
  nav_next_modifier.clear();

  if (!navigation_enabled) {
    return;
  }

  if (params.get("NavDestination").empty()) {
    return;
  }

  const std::string nav_state_raw = params_memory.get("NavInstructionState");
  if (nav_state_raw.empty()) {
    return;
  }

  const QJsonDocument nav_state_doc = QJsonDocument::fromJson(QByteArray::fromStdString(nav_state_raw));
  if (!nav_state_doc.isObject()) {
    return;
  }

  const QJsonObject nav = nav_state_doc.object();
  if (!nav.value("valid").toBool(false)) {
    return;
  }

  nav_primary_text = nav.value("maneuverPrimaryText").toString().trimmed();
  if (nav_primary_text.isEmpty()) {
    return;
  }

  navigation_valid = true;
  nav_secondary_text = nav.value("maneuverSecondaryText").toString().trimmed();
  nav_distance = formatNavDistance(static_cast<float>(nav.value("maneuverDistance").toDouble(0.0)));
  nav_maneuver_type = nav.value("maneuverType").toString().trimmed();
  nav_modifier = nav.value("maneuverModifier").toString().trimmed();
  nav_next_maneuver_type = nav.value("nextManeuverType").toString().trimmed();
  nav_next_modifier = nav.value("nextManeuverModifier").toString().trimmed();
  navigation_has_next = !nav_next_maneuver_type.isEmpty() || !nav_next_modifier.isEmpty();
  navigation_collapsed = params_memory.getBool("NavInstructionCollapsed");
}

void HudRenderer::draw(QPainter &p, const QRect &surface_rect) {
  p.save();

  // Draw header gradient — constant stops, build once
  static const QLinearGradient bg = []() {
    QLinearGradient g(0, UI_HEADER_HEIGHT - (UI_HEADER_HEIGHT / 2.5), 0, UI_HEADER_HEIGHT);
    g.setColorAt(0, QColor::fromRgbF(0, 0, 0, 0.45));
    g.setColorAt(1, QColor::fromRgbF(0, 0, 0, 0));
    return g;
  }();
  p.fillRect(0, 0, surface_rect.width(), UI_HEADER_HEIGHT, bg);


  if (is_cruise_available) {
    drawSetSpeed(p, surface_rect);
  }
  if (starpilot_nvg->standstillDuration == 0 && !starpilot_toggles.value("hide_speed").toBool()) {
    drawCurrentSpeed(p, surface_rect);
  }
  if (navigation_valid) {
    drawNavigationCard(p, surface_rect);
  }

  p.restore();
}

void HudRenderer::drawSetSpeed(QPainter &p, const QRect &surface_rect) {
  // Draw outer box + border to contain set speed
  const QSize default_size = {172, 204};
  QSize set_speed_size = is_metric ? QSize(200, 204) : default_size;

  if (starpilot_nvg->speedLimitHeight != 0) {
    set_speed_size.rheight() += starpilot_nvg->speedLimitHeight;
    if (starpilot_toggles.value("speed_limit_vienna").toBool()) {
      set_speed_size.rwidth() = 200;
    }
  }

  QRect set_speed_rect(QPoint(60 + (default_size.width() - set_speed_size.width()) / 2, 45), set_speed_size);

  if (!starpilot_toggles.value("hide_max_speed").toBool()) {
    // Draw set speed box
    p.setPen(QPen(QColor(255, 255, 255, 75), 6));
    p.setBrush(QColor(0, 0, 0, 166));
    p.drawRoundedRect(set_speed_rect, 32, 32);

    // Colors based on status
    QColor max_color = QColor(0xa6, 0xa6, 0xa6, 0xff);
    QColor set_speed_color = QColor(0x72, 0x72, 0x72, 0xff);
    if (is_cruise_set) {
      set_speed_color = QColor(255, 255, 255);
      if (status == STATUS_DISENGAGED) {
        max_color = QColor(255, 255, 255);
      } else if (status == STATUS_OVERRIDE) {
        max_color = QColor(0x91, 0x9b, 0x95, 0xff);
      } else {
        max_color = QColor(0x80, 0xd8, 0xa6, 0xff);
      }
    }

    // Draw "MAX" text
    p.setFont(InterFont(40, QFont::DemiBold));
    p.setPen(max_color);
    p.drawText(set_speed_rect.adjusted(0, 27, 0, 0), Qt::AlignTop | Qt::AlignHCenter, tr("MAX"));

    // Draw set speed
    QString setSpeedStr = is_cruise_set ? QString::number(std::nearbyint(set_speed)) : "–";
    p.setFont(InterFont(90, QFont::Bold));
    p.setPen(set_speed_color);
    p.drawText(set_speed_rect.adjusted(0, 77, 0, 0), Qt::AlignTop | Qt::AlignHCenter, setSpeedStr);
  }

  starpilot_nvg->defaultSize = default_size;
  starpilot_nvg->isCruiseSet = is_cruise_set;
  starpilot_nvg->setSpeedRect = set_speed_rect;
  starpilot_nvg->speed = speed;
}

void HudRenderer::drawCurrentSpeed(QPainter &p, const QRect &surface_rect) {
  QString speedStr = QString::number(std::nearbyint(speed));

  p.setFont(InterFont(176, QFont::Bold));
  drawText(p, surface_rect.center().x(), 210, speedStr);

  p.setFont(InterFont(66));
  drawText(p, surface_rect.center().x(), 290, is_metric ? tr("km/h") : tr("mph"), 200);
}

void HudRenderer::drawText(QPainter &p, int x, int y, const QString &text, int alpha) {
  QRect real_rect = p.fontMetrics().boundingRect(text);
  real_rect.moveCenter({x, y - real_rect.height() / 2});

  p.setPen(QColor(0xff, 0xff, 0xff, alpha));
  p.drawText(real_rect.x(), real_rect.bottom(), text);
}

QString HudRenderer::formatNavDistance(float distance_m) const {
  if (is_metric) {
    if (distance_m < 1000.0f) {
      int step = distance_m < 500.0f ? 25 : 50;
      return QString("%1 m").arg(qRound(distance_m / step) * step);
    }
    float km = distance_m / 1000.0f;
    return km >= 10.0f ? QString("%1 km").arg(static_cast<int>(std::floor(km))) : QString("%1 km").arg(km, 0, 'f', 1);
  }

  float distance_ft = distance_m * METER_TO_FOOT;
  if (distance_ft < 1000.0f) {
    int step = distance_ft <= 100.0f ? 10 : 50;
    return QString("%1 ft").arg(qRound(distance_ft / step) * step);
  }

  float miles = distance_ft / 5280.0f;
  return miles >= 10.0f ? QString("%1 mi").arg(static_cast<int>(std::floor(miles))) : QString("%1 mi").arg(miles, 0, 'f', 1);
}

QString HudRenderer::navigationIconFilename(const QString &maneuver_type, const QString &modifier) const {
  QString normalized_type = maneuver_type.isEmpty() ? "turn" : maneuver_type;
  if (normalized_type == "rotary") {
    normalized_type = "roundabout";
  } else if (normalized_type == "new name" || normalized_type == "continue") {
    normalized_type = "turn";
  }

  if (modifier == "uturn") {
    return "direction_uturn.png";
  }

  static const QHash<QString, QString> suffixes = {
    {"left", "left"},
    {"right", "right"},
    {"straight", "straight"},
    {"slightLeft", "slight_left"},
    {"slightRight", "slight_right"},
    {"sharpLeft", "sharp_left"},
    {"sharpRight", "sharp_right"},
  };

  normalized_type.replace(" ", "_");
  const QString suffix = suffixes.value(modifier, "");
  const QString candidate = suffix.isEmpty() ? QString("direction_%1.png").arg(normalized_type)
                                             : QString("direction_%1_%2.png").arg(normalized_type, suffix);
  const QString candidate_path = QString("../../starpilot/assets/navigation/%1").arg(candidate);
  return QFileInfo::exists(candidate_path) ? candidate : "direction_turn_straight.png";
}

QPixmap HudRenderer::getNavigationIcon(const QString &maneuver_type, const QString &modifier, int size) {
  const QString icon_name = navigationIconFilename(maneuver_type, modifier);
  const QString cache_key = QString("%1|%2").arg(icon_name).arg(size);
  if (!nav_icon_cache.contains(cache_key)) {
    nav_icon_cache.insert(cache_key, loadPixmap(QString("../../starpilot/assets/navigation/%1").arg(icon_name), QSize(size, size)));
  }
  return nav_icon_cache.value(cache_key);
}

QStringList HudRenderer::wrapNavigationText(int max_width, int font_size, const QString &text) const {
  QStringList words = text.split(' ', QString::SkipEmptyParts);
  QStringList lines;
  QString current_line;
  const QFontMetrics metrics(InterFont(font_size, QFont::Bold));

  for (const QString &word : words) {
    QString test_line = current_line.isEmpty() ? word : current_line + " " + word;
    if (metrics.horizontalAdvance(test_line) <= max_width) {
      current_line = test_line;
    } else {
      if (!current_line.isEmpty()) {
        lines.append(current_line);
      }
      current_line = word;
      if (lines.size() >= 2) {
        break;
      }
    }
  }

  if (!current_line.isEmpty() && lines.size() < 2) {
    lines.append(current_line);
  }
  return lines;
}

void HudRenderer::drawNavigationCard(QPainter &p, const QRect &surface_rect) {
  if (navigation_collapsed) {
    const int chip_size = 94;
    const int chip_x = surface_rect.right() - chip_size - 32;
    const int chip_y = surface_rect.width() >= 1200 ? 232 : 204;
    nav_hit_rect = QRect(chip_x, chip_y, chip_size, chip_size);

    p.setPen(Qt::NoPen);
    p.setBrush(QColor(7, 11, 18, 228));
    p.drawRoundedRect(nav_hit_rect, 28, 28);
    p.setPen(QPen(QColor(255, 255, 255, 40), 2));
    p.setBrush(Qt::NoBrush);
    p.drawRoundedRect(nav_hit_rect, 28, 28);

    const int icon_size = 58;
    const QPixmap icon = getNavigationIcon(nav_maneuver_type, nav_modifier, icon_size);
    const int icon_x = chip_x + (chip_size - icon_size) / 2;
    const int icon_y = chip_y + (chip_size - icon_size) / 2;
    p.drawPixmap(icon_x, icon_y, icon);
    return;
  }

  const int container_width = std::clamp(surface_rect.width() - 120, 760, 1080);
  const int container_height = surface_rect.width() >= 1200 ? 238 : 206;
  const int container_x = (surface_rect.width() - container_width) / 2;
  const int container_y = surface_rect.width() >= 1200 ? 332 : 298;
  const int border_radius = container_height == 238 ? 42 : 34;
  const int icon_size = container_height == 238 ? 150 : 122;
  const int icon_padding = container_height == 238 ? 30 : 24;
  const int then_section_width = container_height == 238 ? 180 : 144;
  const int then_icon_size = container_height == 238 ? 105 : 82;
  const int title_font_size = container_height == 238 ? 75 : 58;
  const int secondary_font_size = container_height == 238 ? 34 : 28;
  const int distance_font_size = container_height == 238 ? 48 : 40;
  const int title_top_padding = container_height == 238 ? 10 : 10;
  const int title_line_spacing = container_height == 238 ? 68 : 56;
  const int secondary_bottom_padding = container_height == 238 ? 24 : 20;
  const int secondary_gap = container_height == 238 ? 10 : 8;

  QRect container(container_x, container_y, container_width, container_height);
  nav_hit_rect = container;
  p.setPen(Qt::NoPen);
  p.setBrush(QColor(0, 0, 0, 180));
  p.drawRoundedRect(container, border_radius, border_radius);

  const int icon_x = container_x + icon_padding;
  const int icon_y = container_y + title_top_padding + 4;
  const QPixmap icon = getNavigationIcon(nav_maneuver_type, nav_modifier, icon_size);
  p.drawPixmap(icon_x, icon_y, icon);

  p.setFont(InterFont(distance_font_size, QFont::Bold));
  p.setPen(Qt::white);
  const int distance_width = p.fontMetrics().horizontalAdvance(nav_distance);
  p.drawText(icon_x + (icon_size - distance_width) / 2, container_y + container_height - 18, nav_distance);

  const int text_x = icon_x + icon_size + 53;
  const int right_gutter = icon_padding + (navigation_has_next ? then_section_width : 0);
  const int text_width = container_width - (text_x - container_x) - right_gutter;
  const QStringList title_lines = wrapNavigationText(text_width, title_font_size, nav_primary_text);
  const QFont title_font = InterFont(title_font_size, QFont::Bold);
  const QFontMetrics title_metrics(title_font);
  const int title_baseline = container_y + title_top_padding + title_metrics.ascent();

  p.setFont(title_font);
  p.setPen(Qt::white);
  for (int index = 0; index < title_lines.size() && index < 2; ++index) {
    p.drawText(text_x, title_baseline + index * title_line_spacing, title_lines[index]);
  }

  if (!nav_secondary_text.isEmpty()) {
    const QFont secondary_font = InterFont(secondary_font_size, QFont::Medium);
    const QFontMetrics secondary_metrics(secondary_font);
    const int title_bottom = title_baseline + (std::max(title_lines.size(), 1) - 1) * title_line_spacing + title_metrics.descent();
    const int secondary_max_baseline = container_y + container_height - secondary_bottom_padding - secondary_metrics.descent();
    const int secondary_preferred_baseline = title_bottom + secondary_gap + secondary_metrics.ascent();
    const int secondary_baseline = std::min(secondary_preferred_baseline, secondary_max_baseline);
    p.setFont(secondary_font);
    p.setPen(QColor(255, 255, 255, 180));
    p.drawText(text_x, secondary_baseline, nav_secondary_text);
  }

  if (!navigation_has_next) {
    return;
  }

  const int divider_x = container_x + container_width - then_section_width - 8;
  p.setPen(QPen(QColor(255, 255, 255, 50), 2));
  p.drawLine(divider_x, container_y + 23, divider_x, container_y + container_height - 23);

  p.setFont(InterFont(container_height == 225 ? 53 : 40, QFont::Medium));
  p.setPen(Qt::white);
  const QString then_label = tr("Then");
  const int then_x = divider_x + 15;
  const int then_label_width = p.fontMetrics().horizontalAdvance(then_label);
  p.drawText(then_x + (then_section_width - 23 - then_label_width) / 2, container_y + (container_height == 238 ? 66 : 60), then_label);

  const QPixmap next_icon = getNavigationIcon(nav_next_maneuver_type, nav_next_modifier, then_icon_size);
  const int then_icon_x = then_x + (then_section_width - 23 - then_icon_size) / 2;
  const int then_icon_y = container_y + (container_height == 238 ? 96 : 78);
  p.drawPixmap(then_icon_x, then_icon_y, next_icon);
}
