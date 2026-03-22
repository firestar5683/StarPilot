from collections.abc import Callable

from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.keyboard import Keyboard


class InputDialog(Widget):
  def __init__(self, title: str, default_text: str = "", hint_text: str = "", on_close: Callable[[DialogResult, str], None] | None = None):
    super().__init__()
    self._default_text = default_text
    self._on_close = on_close
    self._dialog_result = DialogResult.NO_ACTION

    self._keyboard = Keyboard(callback=self._on_keyboard_result)
    self._keyboard.set_title(title)
    self._keyboard.set_text(default_text)

  def _on_keyboard_result(self, result: DialogResult):
    if self._dialog_result != DialogResult.NO_ACTION:
      return
    self._dialog_result = result
    if self._on_close:
      self._on_close(result, self._keyboard.text)

  @property
  def result(self) -> DialogResult:
    return self._dialog_result

  @property
  def text(self) -> str:
    return self._keyboard.text

  def show_event(self):
    super().show_event()
    self._dialog_result = DialogResult.NO_ACTION
    self._keyboard.show_event()
    self._keyboard.clear()
    if self._default_text:
      self._keyboard.set_text(self._default_text)

  def _render(self, rect):
    self._keyboard.render(rect)
    return self._dialog_result
