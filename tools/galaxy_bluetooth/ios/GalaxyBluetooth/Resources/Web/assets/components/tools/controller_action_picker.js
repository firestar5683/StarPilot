import { longitudinalModeLayout, LONGITUDINAL_MODE_KEY } from "./longitudinal_mode.mjs"

const stylesheet = new URL("./controller_action_picker.css", import.meta.url).href

const layoutUrl = "/assets/components/tools/device_settings_layout.json?v=settings-tier-1"

function settingsAnchor(key) {
  if (["ExperimentalMode", "ConditionalExperimental", "ConditionalChill"].includes(key)) return LONGITUDINAL_MODE_KEY
  if (["__starpilot_controller_action__:cycle_driving_personality", "__starpilot_favorite_action__:toggle_traffic_mode"].includes(key)) return "CustomPersonalities"
  return key
}

function settingOwner(option, layout) {
  const key = settingsAnchor(option.key || "")
  const sections = longitudinalModeLayout(layout)
  const section = sections.findLast(section => section.params?.some(param => param.key === key))
  return { key, section }
}

export function actionCategory(option, layout = []) {
  const { section } = settingOwner(option, layout)
  if (section) return section.name
  return option.section === "Actions" ? "Controller Actions" : String(option.section || "Other")
}

export function actionHierarchy(option, layout = []) {
  const { key, section } = settingOwner(option, layout)
  if (!section) return []
  const byKey = new Map(section.params.map(param => [param.key, param]))
  const own = byKey.get(key)
  let node = own?.is_parent_toggle || key !== option.key ? own : byKey.get(own?.parent_key)
  const path = [], seen = new Set()
  while (node && !seen.has(node.key)) {
    seen.add(node.key)
    path.unshift({ key: node.key, label: node.label || node.key })
    node = byKey.get(node.parent_key)
  }
  return path
}

export function actionGroups(options, layout = []) {
  const root = { items: [], groups: [] }
  for (const option of options) {
    let node = root
    for (const part of actionHierarchy(option, layout)) {
      let child = node.groups.find(group => group.key === part.key)
      if (!child) { child = { ...part, count: 0, items: [], groups: [] }; node.groups.push(child) }
      child.count++
      node = child
    }
    node.items.push(option)
  }
  const order = new Map(longitudinalModeLayout(layout).flatMap(section => section.params).map((param, i) => [param.key, i]))
  order.set(LONGITUDINAL_MODE_KEY, -1)
  const sort = node => {
    node.groups.sort((a, b) => (order.get(a.key) ?? Infinity) - (order.get(b.key) ?? Infinity))
    node.groups.forEach(sort)
  }
  sort(root)
  return root
}

export function actionCategories(options, layout = []) {
  const available = new Set(options.map(option => actionCategory(option, layout)))
  const ordered = layout.map(section => section.name).filter(name => available.has(name))
  return [...new Set([...ordered, ...available])]
}

export function filterActions(options, query = "", category = "", layout = []) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  return options.filter(option => (!category || actionCategory(option, layout) === category) &&
    words.every(word => [option.label, option.key, option.description, option.picker_label,
      option.picker_description, actionCategory(option, layout), ...actionHierarchy(option, layout).map(part => part.label)].join(" ").toLocaleLowerCase().includes(word)))
}

export function openControllerActionPicker({ theme = "classic", index, trigger, getOptions, getSlot, isDisabled, onSelect, title = `Controller Action #${index + 1}`, slotAttribute = "data-controller-action-slot", noun = "actions" }) {
  if (isDisabled()) return () => {}
  if (!document.querySelector('link[data-controller-picker]')) {
    const link = document.createElement("link")
    link.rel = "stylesheet"
    link.href = stylesheet
    link.dataset.controllerPicker = ""
    document.head.append(link)
  }
  const dialog = document.createElement("dialog")
  dialog.className = `controllerActionDialog ${theme === "dipper" ? "controllerActionDialog--dipper" : "controllerActionDialog--classic"}`
  dialog.setAttribute("aria-labelledby", "controllerActionTitle")
  dialog.innerHTML = `<header><h3 id="controllerActionTitle">Controller Action #${index + 1}</h3><button type="button" data-cancel>Cancel</button></header>
    <p data-current></p>
    <label class="controllerActionSearch">Search all actions<input type="search" placeholder="Search by name, setting or description" autocomplete="off"></label>
    <label class="controllerActionCategory">Category<select aria-label="Category"></select></label>
    <p data-count role="status" aria-live="polite"></p>
    <div class="controllerActionResults"></div>`
  dialog.querySelector("h3").textContent = title
  dialog.querySelector(".controllerActionSearch").firstChild.textContent = `Search all ${noun}`
  const grouped = theme === "dipper"
  const expanded = new Set()
  if (grouped) dialog.querySelector(".controllerActionCategory").hidden = true
  const input = dialog.querySelector("input")
  const category = dialog.querySelector("select")
  const results = dialog.querySelector(".controllerActionResults")
  const current = dialog.querySelector("[data-current]")
  const count = dialog.querySelector("[data-count]")
  const buttonClass = theme === "dipper" ? "gx-btn gx-btn--tonal" : ""
  dialog.querySelector("[data-cancel]").className = buttonClass
  if (theme === "dipper") {
    input.className = "gx-field"
    category.className = "gx-field"
  }
  let signature = ""
  let layout = []
  let closed = false
  let timer
  const fitViewport = () => {
    let zoom = 1
    for (let node = dialog; node; node = node.parentElement) zoom *= Number.parseFloat(getComputedStyle(node).zoom) || 1
    const viewport = window.visualViewport
    dialog.style.maxHeight = `${(viewport?.height || window.innerHeight) / zoom - 24}px`
    dialog.style.maxWidth = `${(viewport?.width || window.innerWidth) / zoom - 24}px`
  }
  const close = () => {
    if (closed) return
    closed = true
    clearInterval(timer)
    window.removeEventListener("resize", fitViewport)
    window.visualViewport?.removeEventListener("resize", fitViewport)
    dialog.close()
    dialog.remove()
    const target = trigger?.isConnected ? trigger : document.querySelector(`[${slotAttribute}="${index}"]`)
    target?.focus({ preventScroll: true })
  }
  dialog.addEventListener("cancel", event => { event.preventDefault(); close() })
  dialog.addEventListener("keydown", event => {
    if (event.key !== "Tab") return
    const controls = [...dialog.querySelectorAll("button:not(:disabled), input, select, summary")].filter(node => node.getClientRects().length)
    const first = controls[0]
    const last = controls[controls.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus()
    }
  })
  dialog.querySelector("[data-cancel]").addEventListener("click", close)
  const render = () => {
    const options = getOptions()
    const slot = getSlot() || {}
    const key = slot.key || ""
    const disabled = isDisabled()
    const next = JSON.stringify([options, key, slot.label, disabled, input.value, category.value])
    if (signature === next) return
    signature = next
    const categories = actionCategories(options, layout)
    const selectedCategory = category.value
    category.replaceChildren(new Option("All categories", ""), ...categories.map(name => new Option(name, name)))
    category.value = categories.includes(selectedCategory) ? selectedCategory : ""
    const selected = options.find(option => option.key === key)
    current.textContent = `Current: ${selected?.label || slot.label || key || "Not configured"}${key && !selected ? " (unavailable)" : ""}`
    const matches = filterActions(options, input.value, category.value, layout)
    count.textContent = disabled ? "Selection is currently unavailable." : `${matches.length} ${matches.length === 1 ? noun.replace(/s$/, "") : noun}`
    const focusedKey = results.contains(document.activeElement) ? document.activeElement.dataset.actionKey : null
    results.replaceChildren()
    const add = (option, categoryName, container = results) => {
      const button = document.createElement("button")
      button.type = "button"
      button.className = `controllerActionOption ${buttonClass}`
      button.dataset.actionKey = option.key
      button.setAttribute("aria-pressed", String(option.key === key))
      button.disabled = disabled
      const title = document.createElement("strong")
      title.textContent = `${option.key === key ? "✓ " : ""}${option.label}`
      const detail = document.createElement("small")
      detail.textContent = [categoryName, option.description].filter(Boolean).join(" · ")
      button.append(title, detail)
      button.addEventListener("click", () => {
        if (isDisabled() || (option.key && !getOptions().some(item => item.key === option.key))) { render(); return }
        close()
        onSelect(option.key)
      })
      container.append(button)
      if (focusedKey === option.key) button.focus({ preventScroll: true })
    }
    add({ key: "", label: "Not configured", description: "Clear this assignment" }, "")
    if (grouped) {
      for (const name of categories) {
        const items = matches.filter(option => actionCategory(option, layout) === name)
        if (!items.length) continue
        const group = document.createElement("details")
        group.className = "controllerActionGroup"
        group.open = !!input.value.trim() || expanded.has(name)
        const summary = document.createElement("summary")
        summary.textContent = `${name} (${items.length})`
        const body = document.createElement("div")
        body.className = "controllerActionGroupItems"
        group.append(summary, body)
        group.addEventListener("toggle", () => {
          if (!input.value.trim()) group.open ? expanded.add(name) : expanded.delete(name)
        })
        results.append(group)
        const populate = (node, container, path) => {
          for (const option of node.items) add(option, path.join(" · "), container)
          for (const child of node.groups) {
            const id = [...path, child.key].join("/")
            const subgroup = document.createElement("details")
            subgroup.className = "controllerActionGroup controllerActionSubgroup"
            subgroup.open = !!input.value.trim() || expanded.has(id)
            const heading = document.createElement("summary")
            heading.textContent = `${child.label} (${child.count})`
            const content = document.createElement("div")
            content.className = "controllerActionGroupItems"
            subgroup.append(heading, content)
            subgroup.addEventListener("toggle", () => {
              if (!input.value.trim()) subgroup.open ? expanded.add(id) : expanded.delete(id)
            })
            container.append(subgroup)
            populate(child, content, [...path, child.label])
          }
        }
        populate(actionGroups(items, layout), body, [name])
      }
    } else {
      for (const option of matches) add(option, actionCategory(option, layout))
    }
    if (!matches.length) {
      const empty = document.createElement("p")
      empty.textContent = "No matching actions. Try another search or category."
      results.append(empty)
    }
  }
  input.addEventListener("input", () => {
    category.value = ""
    render()
    results.scrollTop = 0
  })
  category.addEventListener("change", () => { render(); results.scrollTop = 0 })
  document.body.append(dialog)
  fitViewport()
  window.addEventListener("resize", fitViewport)
  window.visualViewport?.addEventListener("resize", fitViewport)
  render()
  dialog.showModal()
  input.focus()
  fetch(layoutUrl, { cache: "no-store" }).then(response => {
    if (!response.ok) throw new Error("Settings catalogue unavailable")
    return response.json()
  }).then(data => {
    if (closed || !Array.isArray(data)) return
    layout = data.filter(section => section && typeof section.name === "string" && Array.isArray(section.params))
    signature = ""
    render()
  }).catch(() => {})
  timer = setInterval(() => {
    if (!document.querySelector(`[${slotAttribute}="${index}"]`)) close()
    else render()
  }, 250)
  return close
}
