#include "frogpilot/ui/qt/offroad/expandable_multi_option_dialog.h"

#include <QPushButton>
#include <QButtonGroup>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QScrollBar>
#include <QTimer>

#include "selfdrive/ui/qt/widgets/scrollview.h"

ExpandableMultiOptionDialog::ExpandableMultiOptionDialog(const QString &prompt_text,
                                                         const QMap<QString, QStringList> &seriesToModels,
                                                         const QString &current, QWidget *parent)
  : DialogBase(parent), seriesToModels(seriesToModels) {

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
  )");

  QVBoxLayout *main_layout = new QVBoxLayout(container);
  main_layout->setContentsMargins(55, 50, 55, 50);

  QLabel *title = new QLabel(prompt_text, this);
  title->setStyleSheet("font-size: 70px; font-weight: 500;");
  main_layout->addWidget(title, 0, Qt::AlignLeft | Qt::AlignTop);
  main_layout->addSpacing(25);

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
      QPushButton *modelButton = new QPushButton(model);
      modelButton->setCheckable(true);
      modelButton->setChecked(model == current);
      modelButton->setProperty("class", "model-option");

      QObject::connect(modelButton, &QPushButton::toggled, [=](bool checked) mutable {
        if (checked) {
          selection = model;
          confirm_btn->setEnabled(true);
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
          if (selection == model) {
            confirm_btn->setEnabled(false);
          }
          // Reset to default style
          modelButton->setStyleSheet("");
        }
      });

      group->addButton(modelButton);
      seriesLayout->addWidget(modelButton);
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
                                                  const QString &current, QWidget *parent) {
  ExpandableMultiOptionDialog d = ExpandableMultiOptionDialog(prompt_text, seriesToModels, current, parent);
  if (d.exec()) {
    return d.selection;
  }
  return "";
}