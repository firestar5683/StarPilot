#pragma once

#include <QDialog>
#include <QLabel>
#include <QVBoxLayout>
#include <QWidget>
#include <QMap>
#include <QList>
#include <QComboBox>
#include <QMenu>

#include "selfdrive/ui/qt/widgets/input.h"
#include "selfdrive/ui/qt/widgets/scrollview.h"

class ExpandableMultiOptionDialog : public DialogBase {
  Q_OBJECT

public:
  explicit ExpandableMultiOptionDialog(const QString &prompt_text, const QMap<QString, QStringList> &seriesToModels,
                                         const QString &current, QWidget *parent,
                                         const QStringList &userFavorites = QStringList(),
                                         const QStringList &communityFavorites = QStringList(),
                                         const QMap<QString, QString> &modelReleasedDates = QMap<QString, QString>(),
                                         const QMap<QString, QString> &modelFileToNameMap = QMap<QString, QString>(),
                                         const QString &initialSortMode = "alphabetical");
  static QString getSelection(const QString &prompt_text, const QMap<QString, QStringList> &seriesToModels,
                                const QString &current, QWidget *parent,
                                const QStringList &userFavorites = QStringList(),
                                const QStringList &communityFavorites = QStringList(),
                                const QMap<QString, QString> &modelReleasedDates = QMap<QString, QString>(),
                                const QMap<QString, QString> &modelFileToNameMap = QMap<QString, QString>(),
                                const QString &initialSortMode = QString());
  QString selection;

  QString getCurrentSortMode() const { return currentSortMode; }
  QStringList getUserFavorites() const { return userFavorites; }

private:
  void toggleSeries(const QString &series, QPushButton *headerButton, ScrollView *scrollView);
  void toggleFavorite(const QString &modelName);
  void updateSorting();
  void createModelButton(const QString &modelName, QVBoxLayout *layout, QButtonGroup *group);

  QMap<QString, QStringList> seriesToModels;
  QMap<QString, QWidget*> seriesWidgets;
  QMap<QString, bool> seriesExpanded;
  QMap<QString, QPushButton*> modelButtons;
  QMap<QString, QPushButton*> starButtons;

  QStringList userFavorites;
  QStringList communityFavorites;
  QMap<QString, QString> modelReleasedDates;
  QMap<QString, QString> modelFileToNameMap;

  QString currentSortMode;
  QString currentSelection;
};