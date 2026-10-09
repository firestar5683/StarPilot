// Translate the independent AA placement document into the existing editor model.
const clone = (value) => JSON.parse(JSON.stringify(value))

export function editorSnapshot(raw) {
  if (!raw || raw.version !== 1 || !raw.screen || !raw.metadata || !raw.document || !raw.defaults)
    throw new Error(raw?.reason || "Connect Android Auto once to obtain the actual screen.")
  const colors = raw.colors
  const document = (value) => {
    if (value.version !== 1 || value.canvas?.width !== raw.metadata.width || value.canvas?.height !== raw.metadata.height)
      throw new Error("The saved Android Auto layout does not match its screen. Reload before editing.")
    return { version: 4, clock24Hour: value.clock24Hour === true, largeUiGammaTrial: value.largeUiGammaTrial === true, ...(value.widgetOrder ? { widgetOrder: { large: clone(value.widgetOrder) } } : {}), palette: clone(colors.palette), layouts: { large: clone(value.widgets) },
      widgetColors: { large: clone(colors.widgetColors) }, roadColors: { large: clone(colors.roadColors) } }
  }
  return { ...raw, projection: true, activeProfile: "large", document: document(raw.document), defaults: document(raw.defaults),
    metadata: { projection: true, profiles: { large: clone(raw.metadata) },
      paletteFields: Object.entries(colors.palette).map(([id, value]) => ({ id, label: id, default: value })),
      roadColorFields: [{ id: "path", label: "Path", default: "#30FF9CFF" },
        { id: "pathEdge", label: "Path edges", default: "#00FF40FF" }, { id: "laneLines", label: "Lane lines", default: "#FFFFFFFF" }] } }
}

export function projectionPayload(body, metadata) {
  return { revision: body.revision, document: { version: 1,
    canvas: { width: metadata.profiles.large.width, height: metadata.profiles.large.height },
    clock24Hour: body.document.clock24Hour === true,
    largeUiGammaTrial: body.document.largeUiGammaTrial === true,
    ...(body.document.widgetOrder?.large ? { widgetOrder: clone(body.document.widgetOrder.large) } : {}),
    widgets: clone(body.document.layouts.large) } }
}
