// Presentation adapter only: authoritative selection and writes come from the
// guarded endpoint, never from the instantaneous ExperimentalMode output.
export const LONGITUDINAL_MODE_KEY = "LongitudinalControlMode"
export const LONGITUDINAL_MODES = [
  { value: "chill", label: "Chill" },
  { value: "experimental", label: "Experimental" },
  { value: "conditional_experimental", label: "Conditional Experimental" },
  { value: "conditional_chill", label: "Conditional Chill" },
]

export function longitudinalModeLayout(layout) {
  return layout.map(section => {
    const params = section.params || []
    if (!params.some(p => p.key === "ConditionalExperimental")) return section
    const byKey = new Map(params.map(p => [p.key, p]))
    function owner(p) {
      const seen = new Set()
      while (p?.parent_key && !seen.has(p.parent_key)) {
        if (p.parent_key === "ConditionalExperimental") return "conditional_experimental"
        if (p.parent_key === "ConditionalChill") return "conditional_chill"
        seen.add(p.parent_key)
        p = byKey.get(p.parent_key)
      }
      return null
    }
    return { ...section, params: params.flatMap(p => {
      if (p.key === "ConditionalChill" || p.key === "ExperimentalMode") return []
      if (p.key === "ConditionalExperimental") return [{
        key: LONGITUDINAL_MODE_KEY, label: "Longitudinal control mode", data_type: "string",
        ui_type: "dropdown", settings_tier: "simple", options: LONGITUDINAL_MODES, is_parent_toggle: true,
        description: "Chill: conventional speed control. Experimental: model-controlled gas and brakes. Conditional Experimental: Chill, switching to Experimental under your chosen conditions. Conditional Chill: Experimental, switching to Chill for simple cruising.",
      }]
      const mode = owner(p)
      return [{ ...p, ...(mode ? { longitudinal_mode: mode, settings_tier: "simple" } : {}),
        ...(["ConditionalExperimental", "ConditionalChill"].includes(p.parent_key) ? { parent_key: LONGITUDINAL_MODE_KEY } : {}) }]
    }) }
  })
}

export function validLongitudinalSnapshot(data) {
  return !!data && LONGITUDINAL_MODES.some(mode => mode.value === data.mode) &&
    typeof data.locked === "boolean" && typeof data.reason === "string" &&
    typeof data.experimental_confirmed === "boolean" &&
    ["ExperimentalMode", "ConditionalExperimental", "ConditionalChill"].every(key => typeof data.values?.[key] === "boolean")
}
