#pragma once

#include <array>

#include "selfdrive/ui/qt/onroad/buttons.h"

struct FavoriteSlotState {
  bool enabled = false;
  bool show_onroad = false;
  bool value = false;
  QString key;
  QString label;
};

class DrivingPersonalityButton : public QPushButton {
  Q_OBJECT

public:
  explicit DrivingPersonalityButton(QWidget *parent = 0);

  void updateState(const UIState &s, const StarPilotUIState &fs);

private:
  void paintEvent(QPaintEvent *event) override;
  void showEvent(QShowEvent *event) override;
  void updateTheme();

  bool theme_updated;
  bool traffic_mode_active;

  int personality;

  Params params_memory{"", true};

  QMap<int, QPair<QPixmap, QSharedPointer<QMovie>>> icon_map;

  QMovie *currentGif;

  QPixmap currentImg;
};

class FavoriteButton : public QPushButton {
public:
  explicit FavoriteButton(int slot_index, QWidget *parent = 0);

  void updateState();
  bool shouldShow() const;

private:
  void paintEvent(QPaintEvent *event) override;
  void toggleFavorite();

  FavoriteSlotState currentSlot();
  QFont fittedLabelFont(QPainter &p, const QString &label, const QRect &text_rect) const;

  int slot_index;
  FavoriteSlotState slot;

  Params params;
  Params params_memory{"", true};
};
