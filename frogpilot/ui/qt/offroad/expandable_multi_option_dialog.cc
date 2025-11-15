#include "frogpilot/ui/qt/offroad/expandable_multi_option_dialog.h"

#include <QPushButton>
#include <QButtonGroup>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QScrollBar>
#include <QTimer>
#include <QHBoxLayout>
#include <QSpacerItem>
#include <QLayout>
#include <QLayoutItem>
#include <QGridLayout>
#include <QPoint>
#include <QSize>
#include <QSizePolicy>
#include <QSet>
#include <QVector>
#include <QAbstractButton>
#include <QEvent>
#include <QSignalBlocker>
#include <QScroller>
#include <QPointer>

#include <algorithm>

#include "selfdrive/ui/qt/widgets/scrollview.h"

ExpandableMultiOptionDialog::ExpandableMultiOptionDialog(const QString &prompt_text,
                                                           const QMap<QString, QStringList> &seriesToModels,
                                                           const QString &current, QWidget *parent,
                                                           const QStringList &userFavorites,
                                                           const QStringList &communityFavorites,
                                                           const QMap<QString, QString> &modelReleasedDates,
                                                           const QMap<QString, QString> &modelFileToNameMap,
                                                           const QString &initialSortMode)
  : DialogBase(parent), seriesToModels(seriesToModels), currentSortMode(initialSortMode.isEmpty() ? QString("alphabetical") : initialSortMode),
    userFavorites(userFavorites), communityFavorites(communityFavorites), modelReleasedDates(modelReleasedDates),
    modelFileToNameMap(modelFileToNameMap), currentSelection(current) {

  baseSeriesToModels = seriesToModels;

  for (auto it = modelFileToNameMap.constBegin(); it != modelFileToNameMap.constEnd(); ++it) {
    modelNameToFileMap.insert(it.value(), it.key());
  }

  currentSelectionKey = modelNameToFileMap.value(currentSelection);
  if (!currentSelectionKey.isEmpty()) {
    selectionKey = currentSelectionKey;
    selection = modelFileToNameMap.value(currentSelectionKey, currentSelection);
    currentSelection = selection;
  } else {
    selectionKey.clear();
    selection.clear();
    currentSelection.clear();
  }

  QFrame *container = new QFrame(this);
  container->setStyleSheet(R"(
    QFrame { background-color: #1B1B1B; }
    QPushButton {
      height: 135;
      padding: 0px 50px;
      text-align: left;
      font-size: 55px;
      font-weight: 300;
      border-radius: 10px;
      background-color: #4F4F4F;
      border: 2px solid transparent;
    }
    QPushButton.model-option:checked {
      background-color: #465BEA !important;
      border: 3px solid #FFFFFF !important;
      color: white !important;
      font-weight: 500 !important;
    }
    QPushButton:hover { background-color: #5A5A5A; }
    QPushButton.model-option:checked:hover { background-color: #5A6BEA; }
    QPushButton:pressed {
      background-color: #3049F4;
    }
    QPushButton.model-option:checked:pressed {
      background-color: #3049F4;
      border: 3px solid #CCCCCC;
    }
    QPushButton.series-header {
      background-color: #333333;
      font-weight: 500;
      text-align: left;
      padding-left: 80px;
    }
    QPushButton.series-header:hover { background-color: #404040; }
    QPushButton.favorite-button {
      background-color: transparent;
      border: none;
      font-size: 60px;
      padding: 0px;
      margin: 0px;
      min-width: 80px;
      max-width: 80px;
    }
    QPushButton.favorite-button:hover { background-color: #404040; }
    QComboBox {
      background-color: #4F4F4F;
      border: 2px solid transparent;
      border-radius: 10px;
      padding: 10px;
      font-size: 50px;
      color: white;
      min-width: 200px;
    }
    QComboBox:hover { background-color: #5A5A5A; }
    QComboBox::drop-down {
      border: none;
      width: 50px;
    }
    QComboBox::down-arrow {
      image: url("../../frogpilot/assets/toggle_icons/icon_dropdown.png");
      width: 30px;
      height: 30px;
    }
    QComboBox QAbstractItemView {
      background-color: #4F4F4F;
      border: 2px solid #FFFFFF;
      border-radius: 10px;
      color: white;
      selection-background-color: #465BEA;
      font-size: 50px;
    }
  )");

  QVBoxLayout *main_layout = new QVBoxLayout(container);
  main_layout->setContentsMargins(55, 50, 55, 50);

  QLabel *title = new QLabel(prompt_text, this);
  title->setStyleSheet("font-size: 70px; font-weight: 500;");
  main_layout->addWidget(title, 0, Qt::AlignLeft | Qt::AlignTop);
  main_layout->addSpacing(25);

  // Sort controls - simple cycling button
  QHBoxLayout *sortLayout = new QHBoxLayout();
  sortLayout->setContentsMargins(0, 0, 0, 0);
  sortLayout->setSpacing(20);
  sortLayout->addStretch(); // Push to the right

  QLabel *sortLabel = new QLabel(tr("Sort by:"), this);
  sortLabel->setStyleSheet("font-size: 50px; color: white;");
  sortLayout->addWidget(sortLabel);

  QPushButton *sortButton = new QPushButton(tr("Alphabetical"), this);
  sortButton->setStyleSheet(R"(
    QPushButton {
      background-color: #4F4F4F;
      border: 2px solid transparent;
      border-radius: 10px;
      padding: 10px 20px;
      font-size: 50px;
      color: white;
      min-width: 250px;
      text-align: center;
    }
    QPushButton:hover { background-color: #5A5A5A; }
  )");

  // Set initial button text based on sort mode
  if (currentSortMode == "date") {
    sortButton->setText(tr("Date (Newest)"));
  } else if (currentSortMode == "favorites") {
    sortButton->setText(tr("Favorites First"));
  } else {
    sortButton->setText(tr("Alphabetical"));
  }

  QWidget *sortWidget = new QWidget(container);
  sortWidget->setLayout(sortLayout);
  sortWidget->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Maximum);
  sortLayout->setSizeConstraint(QLayout::SetFixedSize);
  sortWidget->setStyleSheet("background: transparent;");

  sortLayout->addWidget(sortButton);

  auto updateSortOverlayGeometry = [sortWidget, sortLayout]() {
    if (!sortWidget) return;
    const QSize hint = sortLayout->sizeHint();
    sortWidget->setFixedSize(hint);
  };
  updateSortOverlayGeometry();

  QObject::connect(sortButton, &QPushButton::clicked, [this, sortButton, updateSortOverlayGeometry]() {
    if (currentSortMode == "alphabetical") {
      currentSortMode = "date";
      sortButton->setText(tr("Date (Newest)"));
    } else if (currentSortMode == "date") {
      currentSortMode = "favorites";
      sortButton->setText(tr("Favorites First"));
    } else {
      currentSortMode = "alphabetical";
      sortButton->setText(tr("Alphabetical"));
    }
    updateSortOverlayGeometry();
    updateSorting();
  });

  listWidgetContainer = new QWidget(this);
  listLayout = new QVBoxLayout(listWidgetContainer);
  listLayout->setSpacing(10);
  listLayout->setContentsMargins(0, 0, 0, 0);

  buttonGroup = new QButtonGroup(listWidgetContainer);
  buttonGroup->setExclusive(true);

  confirmButton = new QPushButton(tr("Select"));
  confirmButton->setObjectName("confirm_btn");
  confirmButton->setEnabled(!selectionKey.isEmpty());

  scrollView = new ScrollView(listWidgetContainer, this);
  scrollView->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
  if (scrollView->viewport()) {
    scrollView->viewport()->installEventFilter(this);
  }

  QWidget *listContainer = new QWidget(container);
  QGridLayout *overlayLayout = new QGridLayout(listContainer);
  overlayLayout->setContentsMargins(0, 0, 0, 0);
  overlayLayout->setSpacing(0);
  overlayLayout->addWidget(scrollView, 0, 0);
  overlayLayout->setRowStretch(0, 1);
  overlayLayout->setColumnStretch(0, 1);
  overlayLayout->addWidget(sortWidget, 0, 0, Qt::AlignRight | Qt::AlignTop);

  // Create series headers and their expandable content
  rebuildModelList(seriesToModels.keys(), seriesToModels);

  main_layout->addWidget(listContainer);
  main_layout->addSpacing(35);

  // Cancel + confirm buttons
  QHBoxLayout *blayout = new QHBoxLayout;
  main_layout->addLayout(blayout);
  blayout->setSpacing(50);

  QPushButton *cancel_btn = new QPushButton(tr("Cancel"));
  QObject::connect(cancel_btn, &QPushButton::clicked, this, &ConfirmationDialog::reject);
  QObject::connect(confirmButton, &QPushButton::clicked, this, &ConfirmationDialog::accept);
  blayout->addWidget(cancel_btn);
  blayout->addWidget(confirmButton);

  QVBoxLayout *outer_layout = new QVBoxLayout(this);
  outer_layout->setContentsMargins(50, 50, 50, 50);
  outer_layout->addWidget(container);

  // Initial sorting
  updateSorting();
}

void ExpandableMultiOptionDialog::toggleSeries(const QString &series, QPushButton *headerButton) {
  if (!headerButton) return;

  QWidget *container = seriesWidgets.value(series, nullptr);
  if (!container) return;

  bool expanded = seriesExpanded[series];
  QString seriesName = series;

  if (expanded) {
    container->hide();
    seriesExpanded[series] = false;
    headerButton->setText("▶ " + seriesName);
  } else {
    container->show();
    seriesExpanded[series] = true;
    headerButton->setText("▼ " + seriesName);

    // Auto-scroll to place the series at the top of the viewport when expanded
    if (scrollView) {
      QPointer<QPushButton> headerPtr(headerButton);
      QPointer<ScrollView> scrollPtr(scrollView);
      QTimer::singleShot(50, [headerPtr, scrollPtr]() {
        if (!scrollPtr || !headerPtr) return;
        QWidget *contents = scrollPtr->widget();
        if (!contents) return;
        if (QScrollBar *vScrollBar = scrollPtr->verticalScrollBar()) {
          QPoint headerTop = headerPtr->mapTo(contents, QPoint(0, 0));
          int targetValue = qMax(headerTop.y() - 20, 0);
          vScrollBar->setValue(targetValue);
        }
      });
    }
  }

  // Update the button's appearance
  headerButton->update();
}

QString ExpandableMultiOptionDialog::getSelection(const QString &prompt_text,
                                                    const QMap<QString, QStringList> &seriesToModels,
                                                    const QString &current, QWidget *parent,
                                                    const QStringList &userFavorites,
                                                    const QStringList &communityFavorites,
                                                    const QMap<QString, QString> &modelReleasedDates,
                                                    const QMap<QString, QString> &modelFileToNameMap,
                                                    const QString &initialSortMode) {
  ExpandableMultiOptionDialog d(prompt_text, seriesToModels, current, parent,
                                 userFavorites, communityFavorites, modelReleasedDates, modelFileToNameMap, initialSortMode);
  if (d.exec()) {
    return d.selection;
  }
  return "";
}

QStringList ExpandableMultiOptionDialog::getUserFavorites() const {
  QStringList filteredFavorites;
  for (const QString &fav : userFavorites) {
    if (modelFileToNameMap.contains(fav) && !filteredFavorites.contains(fav)) {
      filteredFavorites.append(fav);
    }
  }
  return filteredFavorites;
}

bool ExpandableMultiOptionDialog::eventFilter(QObject *obj, QEvent *event) {
  if (scrollView && obj == scrollView->viewport() && event) {
    switch (event->type()) {
      case QEvent::MouseButtonPress:
      case QEvent::MouseButtonRelease:
      case QEvent::MouseButtonDblClick:
      case QEvent::TouchBegin:
      case QEvent::TouchEnd:
      case QEvent::TouchUpdate:
      case QEvent::Gesture:
        if (QScroller *scroller = QScroller::scroller(scrollView->viewport())) {
          if (scroller->state() == QScroller::Scrolling) {
            scroller->stop();
          }
        }
        break;
      default:
        break;
    }
  }
  return DialogBase::eventFilter(obj, event);
}

void ExpandableMultiOptionDialog::createModelButton(const QString &modelKey, const QString &modelName, const QString &displayName,
                                                    QVBoxLayout *layout, QButtonGroup *group) {
  if (modelKey.isEmpty()) {
    return;
  }

  QWidget *modelWidget = new QWidget();
  QHBoxLayout *modelLayout = new QHBoxLayout(modelWidget);
  modelLayout->setContentsMargins(0, 0, 0, 0);
  modelLayout->setSpacing(10);

  // Star button
  QPushButton *starButton = new QPushButton();
  starButton->setProperty("class", "favorite-button");
  starButton->setCheckable(true);
  starButton->setCursor(Qt::PointingHandCursor);
  starButton->setFocusPolicy(Qt::NoFocus);

  // Check if this model is a favorite
  bool isCommunityFav = communityFavorites.contains(modelKey);
  bool isUserFav = userFavorites.contains(modelKey);
  bool isFavorite = isCommunityFav || isUserFav;

  starButton->setChecked(isFavorite);
  starButton->setText(isFavorite ? QString::fromUtf16(u"\u2665") : QString::fromUtf16(u"\u2661"));

  QObject::connect(starButton, &QPushButton::clicked, [this, modelKey]() {
    toggleFavorite(modelKey);
  });

  favoriteButtons[modelKey] = starButton;
  modelLayout->addWidget(starButton);

  // Model button
  QPushButton *modelButton = new QPushButton(displayName);
  modelButton->setCheckable(true);
  modelButton->setProperty("class", "model-option");
  modelButton->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
  modelButton->setCursor(Qt::PointingHandCursor);
  modelButton->setFocusPolicy(Qt::NoFocus);
  modelButton->setProperty("modelKey", modelKey);
  modelButton->setProperty("modelName", modelName);

  group->addButton(modelButton);
  modelButtons[modelKey] = modelButton;
  modelLayout->addWidget(modelButton);

  layout->addWidget(modelWidget);
}

void ExpandableMultiOptionDialog::toggleFavorite(const QString &modelKey) {
  // Update local state
  if (modelKey.isEmpty()) {
    return;
  }

  if (userFavorites.contains(modelKey)) {
    userFavorites.removeAll(modelKey);
  } else {
    userFavorites.append(modelKey);
  }

  updateSorting();
}

void ExpandableMultiOptionDialog::updateSorting() {
  const QString favoritesSeriesName = QStringLiteral("♥ Favorites");
  QMap<QString, QStringList> newSeriesToModels;
  QStringList orderedSeries;
  QSet<QString> validSeries;
  QSet<QString> favoriteModelKeys;
  QSet<QString> availableModelKeys;
  displayOverrides.clear();

  for (auto it = baseSeriesToModels.constBegin(); it != baseSeriesToModels.constEnd(); ++it) {
    const QStringList &models = it.value();
    for (const QString &modelName : models) {
      const QString modelKey = modelNameToFileMap.value(modelName);
      if (!modelKey.isEmpty()) {
        availableModelKeys.insert(modelKey);
      }
    }
  }

  if (currentSortMode == "favorites") {
    QStringList favoritesList;

    for (const QString &modelKey : communityFavorites) {
      if (availableModelKeys.contains(modelKey)) {
        const QString modelName = modelFileToNameMap.value(modelKey);
        favoritesList.append(modelName);
        favoriteModelKeys.insert(modelKey);
        displayOverrides.insert(modelKey, tr("%1 (Community Fav)").arg(modelName));
      }
    }

    for (const QString &modelKey : userFavorites) {
      if (availableModelKeys.contains(modelKey) && !favoriteModelKeys.contains(modelKey)) {
        favoritesList.append(modelFileToNameMap.value(modelKey));
        favoriteModelKeys.insert(modelKey);
      }
    }

    if (!favoritesList.isEmpty()) {
      std::sort(favoritesList.begin(), favoritesList.end());
      newSeriesToModels.insert(favoritesSeriesName, favoritesList);
      orderedSeries.append(favoritesSeriesName);
      validSeries.insert(favoritesSeriesName);
      seriesExpanded.insert(favoritesSeriesName, true);
    } else {
      seriesExpanded.remove(favoritesSeriesName);
    }
  } else {
    seriesExpanded.remove(favoritesSeriesName);
  }

  struct SeriesInfo {
    QString name;
    QStringList models;
    QString newestDate;
  };

  QVector<SeriesInfo> seriesInfos;

  for (auto it = baseSeriesToModels.constBegin(); it != baseSeriesToModels.constEnd(); ++it) {
    QString series = it.key();
    QStringList models = it.value();

    if (currentSortMode == "date") {
      std::sort(models.begin(), models.end(), [this](const QString &a, const QString &b) {
        QString keyA = modelNameToFileMap.value(a);
        QString keyB = modelNameToFileMap.value(b);
        QString dateA = modelReleasedDates.value(keyA, QStringLiteral("1970-01-01"));
        QString dateB = modelReleasedDates.value(keyB, QStringLiteral("1970-01-01"));
        if (dateA == dateB) {
          return a < b;
        }
        return dateA > dateB;
      });
    } else {
      std::sort(models.begin(), models.end());
    }

    if (currentSortMode == "favorites" && !favoriteModelKeys.isEmpty()) {
      QStringList filteredModels;
      for (const QString &modelName : models) {
        QString key = modelNameToFileMap.value(modelName);
        if (!favoriteModelKeys.contains(key)) {
          filteredModels.append(modelName);
        }
      }
      models = filteredModels;
    }

    if (models.isEmpty()) {
      continue;
    }

    QString newestDate = QStringLiteral("1970-01-01");
    for (const QString &modelName : models) {
      const QString key = modelNameToFileMap.value(modelName);
      const QString date = modelReleasedDates.value(key, QStringLiteral("1970-01-01"));
      if (date > newestDate) {
        newestDate = date;
      }
    }

    seriesInfos.push_back({series, models, newestDate});
    newSeriesToModels.insert(series, models);
  }

  if (currentSortMode == "date") {
    std::sort(seriesInfos.begin(), seriesInfos.end(), [](const SeriesInfo &a, const SeriesInfo &b) {
      if (a.newestDate == b.newestDate) {
        return a.name < b.name;
      }
      return a.newestDate > b.newestDate;
    });
  } else {
    std::sort(seriesInfos.begin(), seriesInfos.end(), [](const SeriesInfo &a, const SeriesInfo &b) {
      return a.name < b.name;
    });
  }

  for (const SeriesInfo &info : seriesInfos) {
    orderedSeries.append(info.name);
    validSeries.insert(info.name);
  }

  for (auto it = seriesExpanded.begin(); it != seriesExpanded.end(); ) {
    if (!validSeries.contains(it.key())) {
      it = seriesExpanded.erase(it);
    } else {
      ++it;
    }
  }

  rebuildModelList(orderedSeries, newSeriesToModels);
  refreshFavoriteIcons();
}

void ExpandableMultiOptionDialog::rebuildModelList(const QStringList &orderedSeries, const QMap<QString, QStringList> &newSeriesToModels) {
  if (!listLayout) return;

  if (scrollView) {
    if (QScroller *scroller = QScroller::scroller(scrollView->viewport())) {
      scroller->stop();
    }
  }

  while (QLayoutItem *item = listLayout->takeAt(0)) {
    if (QWidget *w = item->widget()) {
      delete w;
    } else if (QLayout *layout = item->layout()) {
      delete layout;
    }
    delete item;
  }

  if (buttonGroup) {
    if (buttonGroupConnection)
      QObject::disconnect(buttonGroupConnection);
    buttonGroupConnection = QMetaObject::Connection();
    delete buttonGroup;
    buttonGroup = nullptr;
  }

  buttonGroup = new QButtonGroup(listWidgetContainer);
  buttonGroup->setExclusive(true);

  seriesWidgets.clear();
  modelButtons.clear();
  favoriteButtons.clear();

  for (const QString &series : orderedSeries) {
    const QStringList models = newSeriesToModels.value(series);
    if (models.isEmpty()) {
      continue;
    }

    QPushButton *seriesHeader = new QPushButton("▶ " + series);
    seriesHeader->setProperty("class", "series-header");
    seriesHeader->setCheckable(false);

    bool expanded = seriesExpanded.value(series, false);
    seriesExpanded.insert(series, expanded);

    QObject::connect(seriesHeader, &QPushButton::clicked, [this, series, seriesHeader]() {
      toggleSeries(series, seriesHeader);
    });

    QWidget *seriesContainer = new QWidget();
    QVBoxLayout *seriesLayout = new QVBoxLayout(seriesContainer);
    seriesLayout->setContentsMargins(20, 0, 0, 0);
    seriesLayout->setSpacing(10);

    for (const QString &modelName : models) {
      QString modelKey = modelNameToFileMap.value(modelName);
      if (modelKey.isEmpty()) {
        continue;
      }
      QString displayName = displayOverrides.value(modelKey, modelName);
      createModelButton(modelKey, modelName, displayName, seriesLayout, buttonGroup);
    }

    if (expanded) {
      seriesContainer->show();
      seriesHeader->setText("▼ " + series);
    } else {
      seriesContainer->hide();
      seriesHeader->setText("▶ " + series);
    }

    seriesWidgets.insert(series, seriesContainer);

    listLayout->addWidget(seriesHeader);
    listLayout->addWidget(seriesContainer);
  }

  listLayout->addStretch(1);

  seriesToModels = newSeriesToModels;

  listWidgetContainer->updateGeometry();
  listWidgetContainer->adjustSize();
  if (scrollView && scrollView->widget()) {
    scrollView->widget()->updateGeometry();
    scrollView->widget()->adjustSize();
  }

  if (buttonGroupConnection)
    QObject::disconnect(buttonGroupConnection);

  buttonGroupConnection = QObject::connect(
      buttonGroup,
      static_cast<void (QButtonGroup::*)(QAbstractButton *)>(&QButtonGroup::buttonClicked),
      this,
      [this](QAbstractButton *button) {
    if (!button) return;
    const QString modelKey = button->property("modelKey").toString();
    if (modelKey.isEmpty()) return;

    selectionKey = modelKey;
    currentSelectionKey = modelKey;
    selection = modelFileToNameMap.value(modelKey, selection);
    currentSelection = selection;
    if (confirmButton) {
      confirmButton->setEnabled(true);
    }

    updateButtonStyles();
  });

  updateButtonStyles();
}

void ExpandableMultiOptionDialog::refreshFavoriteIcons() {
  for (auto it = favoriteButtons.begin(); it != favoriteButtons.end(); ++it) {
    const QString &modelKey = it.key();
    QPushButton *button = it.value();
    if (!button) continue;

    bool isCommunityFav = communityFavorites.contains(modelKey);
    bool isUserFav = userFavorites.contains(modelKey);
    bool isFavorite = isCommunityFav || isUserFav;

    button->setChecked(isFavorite);
    button->setText(isFavorite ? QString::fromUtf16(u"\u2665") : QString::fromUtf16(u"\u2661"));
  }

  if (confirmButton && !selectionKey.isEmpty()) {
    confirmButton->setEnabled(true);
  }

  updateButtonStyles();
}

void ExpandableMultiOptionDialog::updateButtonStyles() {
  const QString selectedKey = selectionKey;
  const QString selectedStyle = QStringLiteral(
      "QPushButton {"
      "background-color: #465BEA;"
      "border: 3px solid #FFFFFF;"
      "color: white;"
      "font-weight: 500;"
      "height: 135;"
      "padding: 0px 50px;"
      "text-align: left;"
      "font-size: 55px;"
      "border-radius: 10px;"
      "}");

  for (auto it = modelButtons.begin(); it != modelButtons.end(); ++it) {
    const QString &modelKey = it.key();
    QPushButton *button = it.value();
    if (!button) continue;

    const bool isSelected = (!selectedKey.isEmpty() && modelKey == selectedKey);
    QSignalBlocker blocker(button);
    button->setChecked(isSelected);
    button->setStyleSheet(isSelected ? selectedStyle : QString());
  }
}
