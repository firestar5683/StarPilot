import { html } from "/assets/vendor/arrow-core.js"
import { upperFirst } from "/assets/js/utils.js"

function navigate(href) {
  // Avoid importing router.js here: settings.js is loaded by router.js, and
  // a cache-busted router URL would otherwise create a second router module.
  if (typeof window.__theGalaxyNavigate === "function") {
    return window.__theGalaxyNavigate(href)
  }
  window.location.assign(href)
}

export function SettingsView({ params }) {
  const state = {
    selectedSection: params.section,
    selectedSubsection: params.subsection,
    settings: "[]",
    heading: params.section,
  }

  getSettings().then((results) => {
    if (state.selectedSubsection) {
      const setting = results.find((item) => item.key === state.selectedSubsection) ?? {}

      if (!setting.subsettings || Object.keys(setting.subsettings).length === 0) {
        return navigate(`/settings/${state.selectedSection}`)
      }

      state.heading = setting.key
      state.settings = JSON.stringify([
        {
          ...setting,
          description:
            setting.description +
            "<br><br><b>Disabling this will make settings below irrelevant</b>",
          subsettings: undefined,
          expanded: true,
        },
        ...Object.entries(setting.subsettings).map(([key, value]) => ({
          key,
          section: state.selectedSection,
          ...value,
        })),
      ])
      return
    }

    state.settings = JSON.stringify(results)
  })

  return html`
    <div class="settings" id="settingsWrapper">
      <h1>${() => upperFirst(state.heading)} settings</h1>
      ${() => {
        const settings = JSON.parse(state.settings).filter(
          (el) => el.section === state.selectedSection
        )
        return html`<div>${SettingsList(settings)}</div>`
      }}
    </div>
  `
}

function SettingsList(settings) {
  return settings.map((setting) => html`<div>${setting.key}</div>`)
}
