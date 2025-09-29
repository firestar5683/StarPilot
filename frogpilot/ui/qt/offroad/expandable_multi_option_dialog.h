#pragma once

#include <QDialog>
#include <QLabel>
#include <QVBoxLayout>
#include <QWidget>
#include <QMap>
#include <QList>

#include "selfdrive/ui/qt/widgets/input.h"
#include "selfdrive/ui/qt/widgets/scrollview.h"

class ExpandableMultiOptionDialog : public DialogBase {
  Q_OBJECT

public:
  explicit ExpandableMultiOptionDialog(const QString &prompt_text, const QMap<QString, QStringList> &seriesToModels,
                                       const QString &current, QWidget *parent);
  static QString getSelection(const QString &prompt_text, const QMap<QString, QStringList> &seriesToModels,
                              const QString &current, QWidget *parent);
  QString selection;

private:
  void toggleSeries(const QString &series, QPushButton *headerButton, ScrollView *scrollView);
  QMap<QString, QStringList> seriesToModels;
  QMap<QString, QWidget*> seriesWidgets;
  QMap<QString, bool> seriesExpanded;
};