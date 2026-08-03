def should_show_forget_button(*, is_tethering: bool, is_forgetting: bool, is_saved: bool,
                              wrong_password: bool, is_connecting: bool) -> bool:
  return not (is_tethering or is_forgetting) and ((is_saved and not wrong_password) or is_connecting)
