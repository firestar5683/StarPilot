from openpilot.common.params import Params
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigParamControl
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigMultiOptionDialog
from openpilot.selfdrive.ui.mici.layouts.settings.fingerprint_catalog import (
  FingerprintModelOption,
  format_fingerprint_value,
  get_fingerprint_catalog,
  shorten_model_label,
)
from openpilot.selfdrive.ui.layouts.settings.common import restart_needed_callback
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.multilang import tr

class FingerprintLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()

    self._make_options, self._models_by_make, self._models_by_value, self._make_by_model = get_fingerprint_catalog()

    def force_fp_toggle_callback(checked):

      self._update_enabled(checked)
      restart_needed_callback(None)

    # TODO: tr(...)?
    self._force_fingerprint_toggle = BigParamControl(
      "disable auto fingerprint", "ForceFingerprint", toggle_callback=force_fp_toggle_callback,
    )
    self._car_make_btn = BigButton("car make", self._get_display_make())
    self._car_make_btn.set_click_callback(self._open_make_selector)

    self._car_model_btn = BigButton("car model", self._get_display_model())
    self._car_model_btn.set_click_callback(self._open_model_selector)

    # TODO: WIP
    # self._car_variant_btn = BigButton("variant")
    # self.car_variant_btn.set_click_callback(self._open_variant_selector())

    self._scroller.add_widgets([
      self._force_fingerprint_toggle,
      self._car_make_btn,
      self._car_model_btn,
      # self._car_variant_btn # TODO: WIP
    ])

    ui_state.add_offroad_transition_callback(self._update_toggles)

    self._update_toggles()

  def _show_option_dialog(self, title: str, options: list[str], current: str, on_selected):
    dialog_holder: dict[str, BigMultiOptionDialog] = {}

    def on_confirm():
      on_selected(dialog_holder["dialog"].get_selected_option())

    dialog = BigMultiOptionDialog(options=options, default=current, right_btn_callback=on_confirm)
    dialog_holder["dialog"] = dialog
    gui_app.push_widget(dialog)

  def _update_enabled(self, force_fp):
    self._force_fingerprint_toggle.set_enabled(ui_state.is_offroad())
    self._car_make_btn.set_enabled((ui_state.is_offroad() and force_fp))
    self._car_model_btn.set_enabled((ui_state.is_offroad() and force_fp))

  def _update_toggles(self):
    ui_state.update_params()

    force_fp = ui_state.params.get_bool("ForceFingerprint")

    self._force_fingerprint_toggle.set_checked(force_fp)
    self._car_make_btn.set_value(self._get_display_make())
    self._car_model_btn.set_value(self._get_display_model())

    self._update_enabled(force_fp)


  def show_event(self):
    super().show_event()

    self._update_toggles()

  def _get_display_make(self) -> str:
    make = ui_state.params.get("CarMake", encoding="utf-8") or ""
    if make:
      return make

    model = ui_state.params.get("CarModel", encoding="utf-8") or ""
    if model:
      return self._make_by_model.get(model, format_fingerprint_value(model.split("_", 1)[0]))
    return "Select"

  def _get_selected_model_option(self) -> FingerprintModelOption | None:
    model = ui_state.params.get("CarModel", encoding="utf-8") or ""
    if not model:
      return None

    model_name = ui_state.params.get("CarModelName", encoding="utf-8") or ""
    make = ui_state.params.get("CarMake", encoding="utf-8") or self._make_by_model.get(model, "") # FIXME: Skoda is no redering fancy czech S correctly
    if make and model_name:
      for option in self._models_by_make.get(make, ()):
        if option.value == model and option.label == model_name:
          return option

    return self._models_by_value.get(model)

  def _get_display_model(self) -> str:
    selected_option = self._get_selected_model_option()
    if selected_option is not None:
      return selected_option.button_label

    model = ui_state.params.get("CarModel", encoding="utf-8") or ""
    model_name = ui_state.params.get("CarModelName", encoding="utf-8") or ""
    if model:
      model_option = self._models_by_value.get(model)
      if model_option is not None:
        return model_option.button_label

    if model_name:
      return shorten_model_label(self._get_display_make(), model_name)
    if model:
      return format_fingerprint_value(model)
    return "Select"

  def _set_car_make(self, make: str):
    ui_state.params.put("CarMake", make)
    self._car_make_btn.set_value(make)

  def _set_car_model(self, model: str | FingerprintModelOption):
    if isinstance(model, FingerprintModelOption):
      model_option = model
      model_value = model.value
      model_name = model.label
    else:
      model_value = model
      model_option = self._models_by_value.get(model_value)
      model_name = model_option.label if model_option is not None else format_fingerprint_value(model_value)

    make = self._make_by_model.get(model_value)
    if make is not None:
      ui_state.params.put("CarMake", make)
      self._car_make_btn.set_value(make)

    ui_state.params.put("CarModel", model_value)
    ui_state.params.put("CarModelName", model_name)
    self._car_model_btn.set_value(self._get_display_model())
    restart_needed_callback(True)

  def _open_make_selector(self):
    options = list(self._make_options)
    if not options:
      gui_app.push_widget(BigDialog("", "No fingerprint list available"))
      return

    current_make = self._get_display_make()
    default_make = current_make if current_make in options else options[0]

    def on_selected(selected_make: str):
      self._set_car_make(selected_make)
      current_model = ui_state.params.get("CarModel", encoding="utf-8") or ""
      available_models = {option.value for option in self._models_by_make.get(selected_make, ())}
      if current_model not in available_models and self._models_by_make.get(selected_make):
        self._set_car_model(self._models_by_make[selected_make][0])

    self._show_option_dialog("select make", options, default_make, on_selected)

  def _open_model_selector(self):
    make = self._get_display_make()
    model_options = self._models_by_make.get(make, ())
    if not model_options:
      gui_app.push_widget(BigDialog("", "Select a car make first"))
      return

    current_model = ui_state.params.get("CarModel", encoding="utf-8") or ""
    current_model_name = ui_state.params.get("CarModelName", encoding="utf-8") or ""
    option_labels = [option.option_label for option in model_options]
    selected_by_label = {option.option_label: option for option in model_options}
    default_model = next((option.option_label for option in model_options if option.value == current_model and option.label == current_model_name), None)
    if default_model is None:
      default_model = next((option.option_label for option in model_options if option.value == current_model), option_labels[0])

    def on_selected(selected_label: str):
      self._set_car_model(selected_by_label[selected_label])

    self._show_option_dialog("select model", option_labels, default_model, on_selected)

class VehicleLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()

    self._params = Params()

    fingerprint_panel = FingerprintLayoutMici()
    fingerprint_btn = BigButton("fingerprint", "",gui_app.texture("icons_mici/settings/vehicle/fingerprint.png", 58, 64))
    fingerprint_btn.set_click_callback(lambda: gui_app.push_widget(fingerprint_panel))

    # TODO: make it reloadable without restarting ui
    match ui_state.params.get("CarModel"):
      case _:
        vehicle_specific_widgets = tuple()

    self._scroller.add_widgets([
      fingerprint_btn,
      *vehicle_specific_widgets
    ])

    self._font_medium = gui_app.font(FontWeight.MEDIUM)

