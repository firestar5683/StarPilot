#pragma once

#include <QDialog>
#include <QLabel>
#include <QVBoxLayout>
#include <QWidget>
#include <QMap>
#include <QList>
#include <QPointer>
#include <QComboBox>
#include <QMenu>

#include "selfdrive/ui/qt/widgets/input.h"
#include "selfdrive/ui/qt/widgets/scrollview.h"

class QPushButton;
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
  QStringList getUserFavorites() const;

private:
  void toggleSeries(const QString &series, QPushButton *headerButton);
  void toggleFavorite(const QString &modelKey);
  void updateSorting();
  void rebuildModelList(const QStringList &orderedSeries, const QMap<QString, QStringList> &newSeriesToModels);
  void createModelButton(const QString &modelKey, const QString &modelName, const QString &displayName,
                         QVBoxLayout *layout);
  void refreshFavoriteIcons();
  void updateButtonStyles();
  void stopActiveScroll();
  void stopActiveScrollForInteraction();

  QMap<QString, QStringList> seriesToModels;
  QMap<QString, QStringList> baseSeriesToModels;
  QMap<QString, QWidget*> seriesWidgets;
  QMap<QString, bool> seriesExpanded;
  QMap<QString, QList<QPushButton*>> modelButtons;
  QMap<QString, QList<QPushButton*>> favoriteButtons;

  QStringList userFavorites;
  QStringList communityFavorites;
  QMap<QString, QString> modelReleasedDates;
  QMap<QString, QString> modelFileToNameMap;
  QMap<QString, QString> modelNameToFileMap;
  QMap<QString, QString> displayOverrides;

  QString currentSortMode;
  QString currentSelection;
  QString currentSelectionKey;
  QString selectionKey;

  ScrollView *scrollView = nullptr;
  QVBoxLayout *listLayout = nullptr;
  QPushButton *confirmButton = nullptr;
  QWidget *listWidgetContainer = nullptr;
  QPointer<QPushButton> currentSelectionButton;
};
