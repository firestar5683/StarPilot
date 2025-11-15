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
  QVBoxLayout *listLayout = new QVBoxLayout(listWidget);
  listLayout->setSpacing(10);

  QButtonGroup *group = new QButtonGroup(listWidget);
  group->setExclusive(true);

  QPushButton *confirm_btn = new QPushButton(tr("Select"));
  confirm_btn->setObjectName("confirm_btn");
  confirm_btn->setEnabled(false);

  ScrollView *scroll_view = new ScrollView(listWidget, this);
  scroll_view->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

  // Create series headers and their expandable content
  for (const QString &series : seriesToModels.keys()) {
    // Series header button
    QPushButton *seriesHeader = new QPushButton("▶ " + series);
    seriesHeader->setProperty("class", "series-header");
    seriesHeader->setCheckable(false);
    seriesExpanded[series] = false;

    QObject::connect(seriesHeader, &QPushButton::clicked, [this, series, seriesHeader, scroll_view]() {
      toggleSeries(series, seriesHeader, scroll_view);
    });

    listLayout->addWidget(seriesHeader);

    // Container for series models (initially hidden)
    QWidget *seriesContainer = new QWidget();
    QVBoxLayout *seriesLayout = new QVBoxLayout(seriesContainer);
    seriesLayout->setContentsMargins(20, 0, 0, 0);
    seriesLayout->setSpacing(10);
    seriesContainer->hide();

    // Add models for this series
    for (const QString &model : seriesToModels[series]) {
      createModelButton(model, seriesLayout, group);
    }

    seriesWidgets[series] = seriesContainer;
    listLayout->addWidget(seriesContainer);
  }

  // Add stretch to keep buttons spaced correctly
  listLayout->addStretch(1);

  main_layout->addWidget(scroll_view);
  main_layout->addSpacing(35);

  // Cancel + confirm buttons
  QHBoxLayout *blayout = new QHBoxLayout;
  main_layout->addLayout(blayout);
  blayout->setSpacing(50);

  QPushButton *cancel_btn = new QPushButton(tr("Cancel"));
  QObject::connect(cancel_btn, &QPushButton::clicked, this, &ConfirmationDialog::reject);
  QObject::connect(confirm_btn, &QPushButton::clicked, this, &ConfirmationDialog::accept);
  blayout->addWidget(cancel_btn);
  blayout->addWidget(confirm_btn);

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

void ExpandableMultiOptionDialog::createModelButton(const QString &modelName, QVBoxLayout *layout, QButtonGroup *group) {
  QWidget *modelWidget = new QWidget();
  QHBoxLayout *modelLayout = new QHBoxLayout(modelWidget);
  modelLayout->setContentsMargins(0, 0, 0, 0);
  modelLayout->setSpacing(10);

  // Star button
  QPushButton *starButton = new QPushButton();
  starButton->setProperty("class", "star-button");
  starButton->setCheckable(true);

  // Check if this model is a favorite
  bool isCommunityFav = communityFavorites.contains(modelName);
  bool isUserFav = userFavorites.contains(modelName);
  bool isFavorite = isCommunityFav || isUserFav;

  starButton->setChecked(isFavorite);
  starButton->setText(isFavorite ? "♥" : "♡");

  QObject::connect(starButton, &QPushButton::clicked, [this, modelName, starButton]() {
    // Prevent event propagation to model button
    toggleFavorite(modelName);
    bool isCommunityFav = communityFavorites.contains(modelName);
    bool isUserFav = userFavorites.contains(modelName);
    bool isFavorite = isCommunityFav || isUserFav;
    starButton->setText(isFavorite ? "♥" : "♡");
  });

  starButtons[modelName] = starButton;
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
      }
      // Reset to default style
      modelButton->setStyleSheet("");
    }
  });

  group->addButton(modelButton);
  modelButtons[modelName] = modelButton;
  modelLayout->addWidget(modelButton);

  layout->addWidget(modelWidget);
}

void ExpandableMultiOptionDialog::toggleFavorite(const QString &modelName) {
  // Update local state
  if (userFavorites.contains(modelName)) {
    userFavorites.removeAll(modelName);
  } else {
    userFavorites.append(modelName);
  }

  // Persist to params
  // Note: This would need access to params, which we don't have in this dialog
  // The parent should handle persistence when the dialog is accepted
}

void ExpandableMultiOptionDialog::updateSorting() {
  // Rebuild the series with new sorting
  QMap<QString, QStringList> newSeriesToModels;

  if (currentSortMode == "favorites") {
    // Create favorites section
    QStringList favoritesList;
    QSet<QString> favoriteModelKeys;

    // Add community favorites
    for (const QString &modelKey : communityFavorites) {
      if (this->modelFileToNameMap.contains(modelKey)) {
        QString modelName = this->modelFileToNameMap.value(modelKey);
        if (!favoritesList.contains(modelName)) {
          favoritesList.append(modelName);
          favoriteModelKeys.insert(modelKey);
        }
      }
    }

    // Add user favorites
    for (const QString &modelKey : userFavorites) {
      if (this->modelFileToNameMap.contains(modelKey) && !favoriteModelKeys.contains(modelKey)) {
        QString modelName = this->modelFileToNameMap.value(modelKey);
        if (!favoritesList.contains(modelName)) {
          favoritesList.append(modelName);
          favoriteModelKeys.insert(modelKey);
        }
      }
    }

    if (!favoritesList.isEmpty()) {
      newSeriesToModels["⭐ Favorites"] = favoritesList;
    }

    // Add other models by series
    for (const QString &series : seriesToModels.keys()) {
      QStringList models = seriesToModels[series];
      QStringList filteredModels;
      for (const QString &model : models) {
        if (!favoriteModelKeys.contains(this->modelFileToNameMap.key(model))) {
          filteredModels.append(model);
        }
      }
      if (!filteredModels.isEmpty()) {
        newSeriesToModels[series] = filteredModels;
      }
    }
  } else {
    // Copy existing series
    newSeriesToModels = seriesToModels;

    // Sort within each series
    for (QString &series : newSeriesToModels.keys()) {
      if (series == "⭐ Favorites") continue; // Don't sort favorites

      QStringList &models = newSeriesToModels[series];
      if (currentSortMode == "date") {
        // Sort by release date (newest first)
        std::sort(models.begin(), models.end(), [this](const QString &a, const QString &b) {
          QString keyA = this->modelFileToNameMap.key(a);
          QString keyB = this->modelFileToNameMap.key(b);
          QString dateA = this->modelReleasedDates.value(keyA, "2023-01-01");
          QString dateB = this->modelReleasedDates.value(keyB, "2023-01-01");
          return dateA > dateB; // Newest first
        });
      } else {
        // Alphabetical sort
        models.sort();
      }
    }
  }

  // Update the UI with new sorting
  // This would require rebuilding the series containers
  // For now, just update the seriesToModels for reference
  seriesToModels = newSeriesToModels;
}