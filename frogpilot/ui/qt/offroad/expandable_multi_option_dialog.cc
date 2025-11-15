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
#include <QSet>
#include <QAbstractButton>

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

  selection = currentSelection;

  baseSeriesToModels = seriesToModels;

  for (auto it = modelFileToNameMap.constBegin(); it != modelFileToNameMap.constEnd(); ++it) {
    modelNameToFileMap.insert(it.value(), it.key());
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
    QPushButton.star-button {
      background-color: transparent;
      border: none;
      font-size: 60px;
      padding: 0px;
      margin: 0px;
      min-width: 80px;
      max-width: 80px;
    }
    QPushButton.star-button:hover { background-color: #404040; }
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

  QObject::connect(sortButton, &QPushButton::clicked, [this, sortButton]() {
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
    updateSorting();
  });

  sortLayout->addWidget(sortButton);
  main_layout->addLayout(sortLayout);
  main_layout->addSpacing(15);

  QWidget *listWidget = new QWidget(this);
  listLayout = new QVBoxLayout(listWidget);
  listLayout->setSpacing(10);

  buttonGroup = new QButtonGroup(listWidget);
  buttonGroup->setExclusive(true);

  confirmButton = new QPushButton(tr("Select"));
  confirmButton->setObjectName("confirm_btn");
  confirmButton->setEnabled(!currentSelection.isEmpty());

  scrollView = new ScrollView(listWidget, this);
  scrollView->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

  // Create series headers and their expandable content
  rebuildModelList(seriesToModels);

  main_layout->addWidget(scrollView);
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

void ExpandableMultiOptionDialog::toggleSeries(const QString &series, QPushButton *headerButton, ScrollView *scrollView) {
  bool expanded = seriesExpanded[series];
  QWidget *container = seriesWidgets[series];
  QString seriesName = series;

  if (expanded) {
    container->hide();
    seriesExpanded[series] = false;
    headerButton->setText("▶ " + seriesName);
  } else {
    container->show();
    seriesExpanded[series] = true;
    headerButton->setText("▼ " + seriesName);

    // Auto-scroll to show expanded content
    if (scrollView) {
      QTimer::singleShot(50, [container, scrollView]() {
        QRect containerRect = container->geometry();
        QScrollBar *vScrollBar = scrollView->verticalScrollBar();
        if (vScrollBar) {
          int currentValue = vScrollBar->value();
          int containerBottom = containerRect.bottom();
          int viewportHeight = scrollView->viewport()->height();

          // If container extends beyond viewport, scroll to show it
          if (containerBottom > currentValue + viewportHeight) {
            int targetValue = containerBottom - viewportHeight + 50; // Add some padding
            vScrollBar->setValue(targetValue);
          }
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

void ExpandableMultiOptionDialog::createModelButton(const QString &modelKey, const QString &modelName, QVBoxLayout *layout, QButtonGroup *group) {
  if (modelKey.isEmpty()) {
    return;
  }

  QWidget *modelWidget = new QWidget();
  QHBoxLayout *modelLayout = new QHBoxLayout(modelWidget);
  modelLayout->setContentsMargins(0, 0, 0, 0);
  modelLayout->setSpacing(10);

  // Star button
  QPushButton *starButton = new QPushButton();
  starButton->setProperty("class", "star-button");
  starButton->setCheckable(true);

  // Check if this model is a favorite
  bool isCommunityFav = communityFavorites.contains(modelKey);
  bool isUserFav = userFavorites.contains(modelKey);
  bool isFavorite = isCommunityFav || isUserFav;

  starButton->setChecked(isFavorite);
  starButton->setText(isFavorite ? "♥" : "♡");

  QObject::connect(starButton, &QPushButton::clicked, [this, modelKey]() {
    toggleFavorite(modelKey);
  });

  starButtons[modelKey] = starButton;
  modelLayout->addWidget(starButton);

  // Model button
  QPushButton *modelButton = new QPushButton(modelName);
  modelButton->setCheckable(true);
  modelButton->setChecked(modelName == currentSelection);
  modelButton->setProperty("class", "model-option");
  modelButton->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);

  QObject::connect(modelButton, &QPushButton::toggled, [=](bool checked) mutable {
    if (checked) {
      selection = modelName;
      currentSelection = modelName;
      if (confirmButton) {
        confirmButton->setEnabled(true);
      }
      // Enable confirm button logic would go here
      // Manually apply selected style
      modelButton->setStyleSheet("QPushButton {"
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
    } else {
      if (selection == modelName) {
        // Disable confirm button logic would go here
        if (confirmButton) {
          confirmButton->setEnabled(false);
        }
      }
      // Reset to default style
      modelButton->setStyleSheet("");
    }
  });

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
  QMap<QString, QStringList> newSeriesToModels;
  QSet<QString> favoriteModelKeys;

  if (currentSortMode == "favorites") {
    QStringList favoritesList;

    for (const QString &modelKey : communityFavorites) {
      if (modelFileToNameMap.contains(modelKey)) {
        favoritesList.append(modelFileToNameMap.value(modelKey));
        favoriteModelKeys.insert(modelKey);
      }
    }

    for (const QString &modelKey : userFavorites) {
      if (modelFileToNameMap.contains(modelKey) && !favoriteModelKeys.contains(modelKey)) {
        favoritesList.append(modelFileToNameMap.value(modelKey));
        favoriteModelKeys.insert(modelKey);
      }
    }

    if (!favoritesList.isEmpty()) {
      std::sort(favoritesList.begin(), favoritesList.end());
      newSeriesToModels.insert("⭐ Favorites", favoritesList);
      seriesExpanded.insert("⭐ Favorites", true);
    }
  }

  for (auto it = baseSeriesToModels.constBegin(); it != baseSeriesToModels.constEnd(); ++it) {
    QString series = it.key();
    QStringList models = it.value();

    if (currentSortMode == "date") {
      std::sort(models.begin(), models.end(), [this](const QString &a, const QString &b) {
        QString keyA = modelNameToFileMap.value(a);
        QString keyB = modelNameToFileMap.value(b);
        QString dateA = modelReleasedDates.value(keyA, "2023-01-01");
        QString dateB = modelReleasedDates.value(keyB, "2023-01-01");
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

    if (!models.isEmpty()) {
      newSeriesToModels.insert(series, models);
    }
  }

  rebuildModelList(newSeriesToModels);
  refreshFavoriteIcons();
}

void ExpandableMultiOptionDialog::rebuildModelList(const QMap<QString, QStringList> &newSeriesToModels) {
  if (!listLayout) return;

  if (buttonGroup) {
    const auto buttons = buttonGroup->buttons();
    for (QAbstractButton *button : buttons) {
      buttonGroup->removeButton(button);
    }
  }

  while (QLayoutItem *item = listLayout->takeAt(0)) {
    if (QWidget *w = item->widget()) {
      w->deleteLater();
    } else if (QLayout *layout = item->layout()) {
      delete layout;
    }
    delete item;
  }

  seriesWidgets.clear();
  modelButtons.clear();
  starButtons.clear();

  for (auto it = newSeriesToModels.constBegin(); it != newSeriesToModels.constEnd(); ++it) {
    const QString &series = it.key();
    const QStringList &models = it.value();

    QPushButton *seriesHeader = new QPushButton("▶ " + series);
    seriesHeader->setProperty("class", "series-header");
    seriesHeader->setCheckable(false);

    bool expanded = seriesExpanded.value(series, false);
    seriesExpanded.insert(series, expanded);

    QObject::connect(seriesHeader, &QPushButton::clicked, [this, series, seriesHeader]() {
      toggleSeries(series, seriesHeader, scrollView);
    });

    QWidget *seriesContainer = new QWidget();
    QVBoxLayout *seriesLayout = new QVBoxLayout(seriesContainer);
    seriesLayout->setContentsMargins(20, 0, 0, 0);
    seriesLayout->setSpacing(10);

    for (const QString &modelName : models) {
      QString modelKey = modelNameToFileMap.value(modelName);
      createModelButton(modelKey, modelName, seriesLayout, buttonGroup);
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
}

void ExpandableMultiOptionDialog::refreshFavoriteIcons() {
  for (auto it = starButtons.begin(); it != starButtons.end(); ++it) {
    const QString &modelKey = it.key();
    QPushButton *button = it.value();
    if (!button) continue;

    bool isCommunityFav = communityFavorites.contains(modelKey);
    bool isUserFav = userFavorites.contains(modelKey);
    bool isFavorite = isCommunityFav || isUserFav;

    button->setChecked(isFavorite);
    button->setText(isFavorite ? "♥" : "♡");
  }

  if (confirmButton && !selection.isEmpty()) {
    confirmButton->setEnabled(true);
  }
}
