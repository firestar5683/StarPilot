import CarPlay
import UIKit
import CoreFoundation

@MainActor
final class CarPlaySceneDelegate: NSObject, CPTemplateApplicationSceneDelegate, CPTabBarTemplateDelegate, CPSessionConfigurationDelegate {
    private final class GridAction: NSObject {
        var perform: @MainActor () -> Void
        var signature: String
        init(signature: String, perform: @escaping @MainActor () -> Void) {
            self.signature = signature; self.perform = perform
        }
    }
    private let gridActions = NSMapTable<CPGridButton, GridAction>.weakToStrongObjects()
    private final class WeakGrid {
        weak var page: CPGridTemplate?
        init(_ page: CPGridTemplate) { self.page = page }
    }
    private var sessionConfiguration: CPSessionConfiguration?
    private var controller: CPInterfaceController?
    private var timer: Timer?
    private var work: Task<Void, Never>?
    private var overview: CPGridTemplate?
    private var temperatures: CPGridTemplate?
    private var rates: CPGridTemplate?
    private var toggles: CPGridTemplate?
    private var catalogue: [[String: Any]] = []
    private var values: [String: Any] = [:]
    private var valuesSession = ""
    private var valuesAt = Date.distantPast
    private var categoryPage = 0
    private var busy = false
    private var navigating = false
    private final class GridRefresh: NSObject {
        let perform: @MainActor () -> Void
        init(_ perform: @escaping @MainActor () -> Void) { self.perform = perform }
    }
    private let settingsRefresh = NSMapTable<CPGridTemplate, GridRefresh>.weakToStrongObjects()
    private let overflowParents = NSMapTable<CPTemplate, CPTemplate>.weakToStrongObjects()
    private let gridSizes = NSMapTable<CPGridTemplate, NSNumber>.weakToStrongObjects()
    private final class MetricPageState {
        let title: String
        let kind: String
        var index = 0
        init(title: String, kind: String) { self.title = title; self.kind = kind }
    }

    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didConnect interfaceController: CPInterfaceController) {
        controller = interfaceController
        sessionConfiguration = CPSessionConfiguration(delegate: self)
        overview = nil; temperatures = nil; rates = nil; toggles = nil
        let model = AppModel.shared
        model.setCarPlayActive(true)
        refreshTelemetry()
        catalogue = localCatalogue()
        toggles = grid("Toggles", icon: "switch.2", buttons: categoryButtons())
        guard let overview, let temperatures, let rates, let toggles else { return }
        let tabs = CPTabBarTemplate(templates: [overview, temperatures, rates, toggles])
        tabs.delegate = self
        interfaceController.setRootTemplate(tabs, animated: false, completion: nil)
        showCategories()
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refreshTelemetry() }
        }
    }

    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didDisconnectInterfaceController interfaceController: CPInterfaceController) {
        timer?.invalidate(); timer = nil
        work?.cancel(); work = nil
        controller = nil
        sessionConfiguration?.delegate = nil; sessionConfiguration = nil
        overview = nil; temperatures = nil; rates = nil; toggles = nil
        catalogue = []; values = [:]; busy = false; categoryPage = 0; valuesSession = ""; valuesAt = .distantPast
        gridActions.removeAllObjects(); gridSizes.removeAllObjects(); overflowParents.removeAllObjects(); settingsRefresh.removeAllObjects(); navigating = false
        AppModel.shared.setCarPlayActive(false)
    }

    func tabBarTemplate(_ tabBarTemplate: CPTabBarTemplate, didSelect selectedTemplate: CPTemplate) {
        if selectedTemplate === toggles { loadGalaxy() }
    }

    private var carAppearance: UIUserInterfaceStyle {
        if let style = sessionConfiguration?.contentStyle {
            if style.contains(.dark) && !style.contains(.light) { return .dark }
            if style.contains(.light) && !style.contains(.dark) { return .light }
        }
        return controller?.carTraitCollection.userInterfaceStyle == .dark ? .dark : .light
    }

    func sessionConfiguration(_ sessionConfiguration: CPSessionConfiguration, contentStyleChanged contentStyle: CPContentStyle) {
        let appearance: UIUserInterfaceStyle = contentStyle.contains(.dark) && !contentStyle.contains(.light) ? .dark :
            contentStyle.contains(.light) && !contentStyle.contains(.dark) ? .light : carAppearance
        let traits = UITraitCollection(userInterfaceStyle: appearance)
        let templates = controller?.templates ?? []
        var visited = Set<ObjectIdentifier>()
        for template in templates.flatMap({ ($0 as? CPTabBarTemplate)?.templates ?? [$0] }) {
            guard let grid = template as? CPGridTemplate, visited.insert(ObjectIdentifier(grid)).inserted else { continue }
            for button in grid.gridButtons {
                if #available(iOS 26.0, *), let asset = button.image.imageAsset { button.updateImage(asset.image(with: traits)) }
            }
        }
    }

    private func pushTemplate(_ template: CPTemplate, animated: Bool, completion: ((Bool, Error?) -> Void)?) {
        guard let controller, !navigating else { completion?(false, nil); return }
        navigating = true
        let finished: (Bool, Error?) -> Void = { [weak self, weak controller] success, error in
            guard let self, let controller, self.controller === controller else { return }
            self.navigating = false
            completion?(success, error)
            if !success { self.notice(error?.localizedDescription ?? "This page could not be opened.") }
        }
        // A tab container also occupies a hierarchy level. Reserve that level before pushing.
        if controller.templates.count >= 4, let parent = controller.topTemplate {
            controller.popTemplate(animated: false) { [weak self, weak controller] success, error in
                guard let self, let controller, self.controller === controller else { return }
                guard success else { finished(false, error); return }
                self.overflowParents.setObject(parent, forKey: template)
                if let page = template as? CPBarButtonProviding {
                    page.backButton = CPBarButton(image: UIImage(systemName: "chevron.left")!) { [weak self] _ in
                        self?.popTemplate(animated: true, completion: nil)
                    }
                }
                controller.pushTemplate(template, animated: animated, completion: finished)
            }
        } else {
            controller.pushTemplate(template, animated: animated, completion: finished)
        }
    }

    private func popTemplate(animated: Bool, completion: ((Bool, Error?) -> Void)?) {
        guard let controller, !navigating else { completion?(false, nil); return }
        let top = controller.topTemplate
        let parent = top.flatMap { overflowParents.object(forKey: $0) }
        navigating = true
        controller.popTemplate(animated: animated) { [weak self, weak controller] success, error in
            guard let self, let controller, self.controller === controller else { return }
            guard success else { self.navigating = false; completion?(false, error); return }
            if let top { self.overflowParents.removeObject(forKey: top) }
            if let parent {
                controller.pushTemplate(parent, animated: false) { [weak self] restored, error in
                    self?.navigating = false; completion?(restored, error)
                }
            } else {
                self.navigating = false; completion?(true, nil)
            }
        }
    }

    private func paddedButtons(_ buttons: [CPGridButton], capacity: Int = 8) -> [CPGridButton] {
        var result = Array(buttons.prefix(capacity))
        while result.count < capacity {
            let empty = UIGraphicsImageRenderer(size: CGSize(width: 1, height: 1)).image { _ in }
            let action = GridAction(signature: "empty", perform: {})
            let spacer = CPGridButton(titleVariants: [" "], image: empty) { _ in action.perform() }
            gridActions.setObject(action, forKey: spacer)
            spacer.isEnabled = false
            result.append(spacer)
        }
        return result
    }

    private func makeGrid(title: String?, gridButtons: [CPGridButton], compact: Bool = false) -> CPGridTemplate {
        let capacity = compact ? 4 : 8
        let page = CPGridTemplate(title: title, gridButtons: paddedButtons(gridButtons, capacity: capacity))
        gridSizes.setObject(NSNumber(value: capacity), forKey: page)
        return page
    }

    private func grid(_ title: String, icon: String, buttons: [CPGridButton]) -> CPGridTemplate {
        precondition(!buttons.isEmpty)
        let template = makeGrid(title: title, gridButtons: buttons)
        template.tabTitle = title
        template.tabImage = UIImage(systemName: icon)
        return template
    }

    private func button(_ title: String, icon: String, value: String? = nil, action: @escaping @MainActor () -> Void = {}) -> CPGridButton {
        let configuration = UIImage.SymbolConfiguration(pointSize: 32, weight: .regular)
        let symbol = UIImage(systemName: icon, withConfiguration: configuration) ?? UIImage(systemName: "circle")!
        let image: UIImage
        if let value {
            let format = UIGraphicsImageRendererFormat()
            format.scale = controller?.carTraitCollection.displayScale ?? 2
            let text = value.replacingOccurrences(of: " °C", with: "°").replacingOccurrences(of: " FPS", with: "")
            let asset = UIImageAsset()
            for (style, color) in [(UIUserInterfaceStyle.light, UIColor.black), (.dark, UIColor.white)] {
                let rendered = UIGraphicsImageRenderer(size: CGSize(width: 72, height: 72), format: format).image { _ in
                    if value == "On" || value == "Off" {
                        let on = value == "On"
                        (on ? UIColor.systemGreen : (style == .dark ? UIColor.darkGray : UIColor.systemGray)).setFill()
                        UIBezierPath(roundedRect: CGRect(x: 3, y: 7, width: 66, height: 36), cornerRadius: 18).fill()
                        UIColor.white.setFill()
                        UIBezierPath(ovalIn: CGRect(x: on ? 36 : 6, y: 10, width: 30, height: 30)).fill()
                    } else {
                        symbol.withTintColor(color, renderingMode: .alwaysOriginal).draw(in: CGRect(x: 22, y: 0, width: 28, height: 28))
                    }
                    let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center
                    let size: CGFloat = text.count <= 6 ? 24 : text.count <= 10 ? 18 : 14
                    (text as NSString).draw(in: CGRect(x: 0, y: value == "On" || value == "Off" ? 47 : 36, width: 72, height: 25), withAttributes: [
                        .font: UIFont.monospacedDigitSystemFont(ofSize: size, weight: .semibold),
                        .foregroundColor: color, .paragraphStyle: paragraph
                    ])
                }.withRenderingMode(.alwaysOriginal)
                asset.register(rendered, with: UITraitCollection(traitsFrom: [
                    UITraitCollection(userInterfaceStyle: style), UITraitCollection(displayScale: format.scale)
                ]))
            }
            image = asset.image(with: UITraitCollection(traitsFrom: [
                UITraitCollection(userInterfaceStyle: carAppearance), UITraitCollection(displayScale: format.scale)
            ]))
        } else { image = symbol.withRenderingMode(.alwaysTemplate) }
        let label = title
        let state = GridAction(signature: "\(title)|\(icon)|\(value ?? "")", perform: action)
        let result = CPGridButton(titleVariants: [label, compactCaption(label)], image: image) { _ in state.perform() }
        gridActions.setObject(state, forKey: result)
        return result
    }

    private func compactCaption(_ label: String) -> String {
        label.replacingOccurrences(of: "Advanced ", with: "Adv. ")
            .replacingOccurrences(of: "Longitudinal", with: "Speed")
            .replacingOccurrences(of: "Lateral", with: "Steering")
            .replacingOccurrences(of: "Acceleration", with: "Accel.")
            .replacingOccurrences(of: "Deceleration", with: "Braking")
            .replacingOccurrences(of: "Conditional ", with: "")
            .replacingOccurrences(of: "Controller", with: "Control")
    }

    private func updateGrid(_ page: CPGridTemplate, buttons rawButtons: [CPGridButton]) {
        precondition(!rawButtons.isEmpty)
        let buttons = paddedButtons(rawButtons, capacity: gridSizes.object(forKey: page)?.intValue ?? 8)
        if #available(iOS 26.0, *), page.gridButtons.count == buttons.count {
            for (existing, replacement) in zip(page.gridButtons, buttons) {
                guard let current = gridActions.object(forKey: existing),
                      let next = gridActions.object(forKey: replacement) else {
                    page.updateGridButtons(buttons)
                    return
                }
                current.perform = next.perform
                existing.isEnabled = replacement.isEnabled
                if current.signature != next.signature {
                    existing.updateTitleVariants(replacement.titleVariants)
                    existing.updateImage(replacement.image)
                    current.signature = next.signature
                }
            }
        } else {
            page.updateGridButtons(buttons)
        }
    }

    private func telemetryGrid(_ existing: CPGridTemplate?, title: String, icon: String,
                               buttons: [CPGridButton]) -> CPGridTemplate {
        if let existing { updateGrid(existing, buttons: buttons); return existing }
        return grid(title, icon: icon, buttons: buttons)
    }

    private func external(_ metric: DiagnosticMetric) -> Bool {
        let name = metric.name.lowercased()
        return name.contains("external gpu") || name.contains("chestnut") || name.hasPrefix("sensor: amdgpu")
    }

    private func thermalGroup(_ metric: DiagnosticMetric) -> String {
        let name = metric.name.lowercased()
        if external(metric) { return "External GPU" }
        if name.hasPrefix("sensor:") { return "Other sensors" }
        if name.contains("cpu") || name.contains("dsp") || name.contains("soc") { return "Processors" }
        if name.contains("gpu") { return "Onboard GPU" }
        if name.contains("memory") { return "Memory" }
        if name.contains("intake") || name.contains("exhaust") { return "Cooling" }
        if name.contains("pmic") { return "Power" }
        if name.contains("modem") || name.contains("gnss") { return "Connectivity" }
        return "Other sensors"
    }

    private func thermalLabel(_ group: String) -> String {
        switch group {
        case "Processors": return "CPU / DSP"
        case "Onboard GPU": return "GPU"
        case "Connectivity": return "Radios"
        case "Other sensors": return "Sensors"
        default: return group
        }
    }

    private func thermalIcon(_ group: String) -> String {
        switch group {
        case "Processors", "Onboard GPU", "External GPU": return "cpu"
        case "Memory": return "memorychip"
        case "Cooling": return "fan"
        case "Power": return "bolt"
        case "Connectivity": return "antenna.radiowaves.left.and.right"
        default: return "thermometer.medium"
        }
    }

    private func maximum(_ metrics: [DiagnosticMetric]) -> String {
        guard let value = metrics.compactMap(\.value).filter(\.isFinite).max() else { return "—" }
        return String(format: "%.1f °C", value)
    }

    private func refreshTelemetry() {
        let model = AppModel.shared
        let system = model.diagnostics.fresh ? model.diagnostics.system ?? [:] : [:]
        let memory = system["memory"] as? [String: Any] ?? [:]
        let storage = system["storage"] as? [String: Any] ?? [:]
        func value(_ source: [String: Any], _ key: String, _ unit: String) -> String {
            guard let number = source[key] as? NSNumber, number.doubleValue.isFinite else { return "—" }
            return String(format: "%.1f %@", number.doubleValue, unit)
        }
        overview = telemetryGrid(overview, title: "Overview", icon: "sparkles", buttons: [
            button(model.transport.label, icon: "antenna.radiowaves.left.and.right"),
            button("CPU", icon: "cpu", value: value(system, "cpuPercent", "%")),
            button("Memory", icon: "memorychip", value: value(memory, "percent", "%")),
            button("Storage used", icon: "internaldrive", value: value(storage, "usedGiB", "GiB")),
            button("Uptime", icon: "clock", value: value(system, "uptimeSeconds", "s")),
            button("Processes", icon: "list.bullet", value: value(system, "processCount", ""))
        ])
        let cores = system["cores"] as? [[String: Any]] ?? []
        rates = telemetryGrid(rates, title: "CPU", icon: "cpu", buttons: cores.isEmpty ? [button("Waiting for CPU readings", icon: "cpu")] : cores.prefix(8).map {
            button($0["name"] as? String ?? "CPU", icon: "cpu", value: value($0, "percent", "%"))
        })
        temperatures = telemetryGrid(temperatures, title: "Memory", icon: "memorychip", buttons: [
            button("Used", icon: "memorychip", value: value(memory, "usedMiB", "MiB")),
            button("Available", icon: "memorychip", value: value(memory, "availableMiB", "MiB")),
            button("Total", icon: "memorychip", value: value(memory, "totalMiB", "MiB")),
            button("Storage total", icon: "internaldrive", value: value(storage, "totalGiB", "GiB"))
        ])
    }

    private func rateGroup(_ metric: DiagnosticMetric) -> String {
        let name = metric.name.lowercased()
        if external(metric) { return "external" }
        if name.contains("camera") { return "cameras" }
        if name.contains("model") || name.contains("plan") { return "models" }
        if name.contains("carstate") || name.contains("carcontrol") || name.contains("selfdrive") { return "driving" }
        if name == "ui" { return "display" }
        return "other"
    }

    private func showMetrics(_ title: String, kind: String) {
        guard controller != nil else { return }
        let page = makeGrid(title: title, gridButtons: [button("Loading readings…", icon: "hourglass")])
        page.userInfo = MetricPageState(title: title, kind: kind)
        updateMetrics(page)
        pushTemplate(page, animated: true, completion: nil)
    }

    private func updateMetrics(_ page: CPGridTemplate) {
        guard let state = page.userInfo as? MetricPageState else { return }
        let diagnostics = AppModel.shared.diagnostics
        guard diagnostics.fresh, let sample = diagnostics.snapshot else {
            updateGrid(page, buttons: [button("Telemetry unavailable", icon: "exclamationmark.triangle") { [weak self] in self?.notice(diagnostics.status) }])
            return
        }
        let readings = sample.temperatures.filter { thermalGroup($0) == state.kind } + sample.rates.filter { rateGroup($0) == state.kind }
        let count = max(1, (readings.count + 7) / 8)
        state.index = min(state.index, count - 1)
        var buttons = readings.dropFirst(state.index * 8).prefix(8).map { button($0.name, icon: "gauge", value: $0.display) }
        if buttons.isEmpty { buttons = [button("No readings available", icon: "questionmark.circle")] }
        paging(page, index: state.index, count: count) { [weak self, weak page] index in
            guard let self, let page else { return }; state.index = index; self.updateMetrics(page)
        }
        page.updateTitle(count > 1 ? "\(state.title) · \(state.index + 1)/\(count)" : state.title)
        updateGrid(page, buttons: buttons)
    }

    private final class SettingsPageState {
        let name: String
        var snapshot: [String: Any] = [:]
        var session = ""
        var index = 0
        init(_ name: String) { self.name = name }
    }
    private var session: String {
        let model = AppModel.shared
        return model.transport.usesLAN ? "lan-" + model.lan.generation : "ble-" + model.bluetooth.sessionIdentifier
    }
    private func request(_ path: String, payload: [String: Any]? = nil) async throws -> [String: Any] {
        let original = session
        let response = try await AppModel.shared.transport.request(path: path, method: payload == nil ? "GET" : "POST",
            headers: payload == nil ? [:] : ["Content-Type": "application/json"],
            body: try payload.map { try JSONSerialization.data(withJSONObject: $0) } ?? Data())
        try Task.checkCancellation()
        guard original == session else { throw BridgeError.message("Connection changed. Refresh the page.") }
        let data = (try? JSONSerialization.jsonObject(with: response.bodyData)) as? [String: Any] ?? [:]
        guard response.status == 200 else {
            throw BridgeError.message(data["error"] as? String ?? "Galaxy request failed (HTTP \(response.status)).")
        }
        return data
    }
    private func localCatalogue() -> [[String: Any]] { [] }
    private func categoryButtons() -> [CPGridButton] {
        [button("Open toggles", icon: "switch.2") { [weak self] in self?.loadGalaxy() }]
    }
    private func showCategories() { loadGalaxy() }
    private func loadGalaxy() {
        guard let toggles else { return }
        if toggles.userInfo == nil { toggles.userInfo = SettingsPageState("hub") }
        loadSettings(toggles)
    }
    private func openSettings(_ name: String, title: String) {
        let page = makeGrid(title: title, gridButtons: [button("Loading…", icon: "hourglass")])
        page.userInfo = SettingsPageState(name)
        pushTemplate(page, animated: true) { [weak self, weak page] success, _ in
            if success, let page { self?.loadSettings(page) }
        }
    }
    private func loadSettings(_ page: CPGridTemplate) {
        guard let state = page.userInfo as? SettingsPageState, !busy else { return }
        work?.cancel()
        work = Task { [weak self, weak page] in
            guard let self, let page else { return }
            do {
                let name = state.name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed.subtracting(CharacterSet(charactersIn: "/")))!
                state.snapshot = try await self.request("/api/settings/pages/" + name)
                state.session = self.session
                self.drawSettings(page)
            } catch {
                if !Task.isCancelled {
                    self.updateGrid(page, buttons: [self.button("Retry", icon: "arrow.clockwise") { [weak self, weak page] in
                        if let page { self?.loadSettings(page) }
                    }])
                    self.notice(error.localizedDescription)
                }
            }
        }
    }
    private func drawSettings(_ page: CPGridTemplate) {
        guard let state = page.userInfo as? SettingsPageState else { return }
        let rows = state.snapshot["rows"] as? [[String: Any]] ?? []
        let count = max(1, (rows.count + 7) / 8)
        state.index = min(state.index, count - 1)
        var buttons: [CPGridButton] = []
        for index in (state.index * 8)..<min(rows.count, (state.index + 1) * 8) {
            let row = rows[index]
            let child = row["page"] as? String ?? ""
            let value = row["value"].map { String(describing: $0) } ?? ""
            let choices = row["choices"] as? [String] ?? []
            let icon = !child.isEmpty ? "folder" : choices.contains("On") && choices.contains("Off") ?
                (value == "On" ? "switch.2" : "switch.2") : "slider.horizontal.3"
            let tile = button(row["label"] as? String ?? "Setting", icon: icon, value: child.isEmpty ? value : nil) { [weak self, weak page] in
                guard let self, let page else { return }
                guard state.session == self.session else { self.loadSettings(page); return }
                if !child.isEmpty { self.openSettings(child, title: row["label"] as? String ?? "Toggles") }
                else { self.editSetting(page, index: index, row: row) }
            }
            tile.isEnabled = row["available"] as? Bool == true && (!child.isEmpty || row["action"] as? Bool == true) && !busy
            buttons.append(tile)
        }
        updateGrid(page, buttons: buttons.isEmpty ? [button("No settings available", icon: "info.circle")] : buttons)
        var navigation: [CPBarButton] = []
        if state.index > 0 {
            navigation.append(CPBarButton(image: UIImage(systemName: "chevron.left")!) { [weak self, weak page] _ in
                guard let page else { return }; state.index -= 1; self?.drawSettings(page)
            })
        }
        if state.index + 1 < count {
            navigation.append(CPBarButton(image: UIImage(systemName: "chevron.right")!) { [weak self, weak page] _ in
                guard let page else { return }; state.index += 1; self?.drawSettings(page)
            })
        }
        page.trailingNavigationBarButtons = navigation
    }
    private func editSetting(_ parent: CPGridTemplate, index: Int, row: [String: Any]) {
        let choices = row["choices"] as? [String] ?? []
        if choices.count == 2, choices.contains("On"), choices.contains("Off") {
            preview(parent, index: index, selection: row["value"] as? String == "On" ? "Off" : "On")
            return
        }
        let editor = makeGrid(title: row["label"] as? String, gridButtons: [button("Loading…", icon: "hourglass")])
        var buttons: [CPGridButton] = []
        if !choices.isEmpty {
            var choicePage = 0
            func redraw() {
                let count = max(1, (choices.count + 7) / 8)
                let start = choicePage * 8
                let tiles = choices[start..<min(start + 8, choices.count)].map { choice in
                    button(choice, icon: String(describing: row["value"] ?? "") == choice ? "checkmark.circle.fill" : "circle") { [weak self] in
                        self?.preview(parent, index: index, selection: choice)
                    }
                }
                updateGrid(editor, buttons: tiles)
                paging(editor, index: choicePage, count: count) { next in choicePage = next; redraw() }
            }
            redraw()
            pushTemplate(editor, animated: true, completion: nil)
            return
        } else if (row["step"] as? NSNumber)?.doubleValue ?? 0 > 0 {
            buttons = [button("Decrease", icon: "minus.circle", value: String(describing: row["value"] ?? "")) { [weak self] in self?.preview(parent, index: index, direction: -1) },
                       button("Increase", icon: "plus.circle", value: String(describing: row["value"] ?? "")) { [weak self] in self?.preview(parent, index: index, direction: 1) }]
        } else {
            buttons = [button("Continue", icon: "checkmark.circle") { [weak self] in self?.preview(parent, index: index, direction: 0) }]
        }
        updateGrid(editor, buttons: buttons)
        pushTemplate(editor, animated: true, completion: nil)
    }
    private func preview(_ page: CPGridTemplate, index: Int, selection: String? = nil, direction: Int = 0) {
        guard !busy, let state = page.userInfo as? SettingsPageState, state.session == session,
              let view = state.snapshot["view"] as? String else { loadSettings(page); return }
        busy = true
        let original = session
        Task { [weak self, weak page] in
            guard let self, let page else { return }
            defer { self.busy = false }
            do {
                var payload: [String: Any] = ["view": view, "row": index, "direction": direction]
                if let selection { payload["value"] = selection }
                let pending = try await self.request("/api/settings/preview", payload: payload)
                guard let intent = pending["intent"] as? String else { throw BridgeError.message("Refresh settings and try again.") }
                let confirm = CPAlertAction(title: "Save", style: .default) { [weak self, weak page] _ in
                    guard let self, let page else { return }
                    self.controller?.dismissTemplate(animated: true) { _, _ in
                        guard original == self.session else { self.notice("Connection changed. Refresh settings."); return }
                        self.commit(intent, page: page)
                    }
                }
                let cancel = CPAlertAction(title: "Cancel", style: .cancel) { [weak self] _ in self?.controller?.dismissTemplate(animated: true, completion: nil) }
                self.controller?.presentTemplate(CPAlertTemplate(titleVariants: [pending["question"] as? String ?? "Save this preference?"], actions: [cancel, confirm]), animated: true, completion: nil)
            } catch { self.notice(error.localizedDescription); self.busy = false; self.loadSettings(page) }
        }
    }
    private func commit(_ intent: String, page: CPGridTemplate) {
        guard !busy else { return }
        busy = true
        Task { [weak self, weak page] in
            guard let self, let page else { return }
            do {
                let result = try await self.request("/api/settings/confirm", payload: ["intent": intent, "confirmed": true])
                if result["saved"] as? Bool != true { self.notice("Save could not be confirmed. Check the current value.") }
            } catch { self.notice(error.localizedDescription) }
            self.busy = false
            if self.controller?.topTemplate !== page {
                self.popTemplate(animated: true) { [weak self, weak page] _, _ in
                    if let page { self?.loadSettings(page) }
                }
            } else { self.loadSettings(page) }
        }
    }
    private func paging(_ page: CPGridTemplate, index: Int, count: Int, change: @escaping @MainActor (Int) -> Void) {
        var items: [CPBarButton] = []
        if index > 0 { items.append(CPBarButton(image: UIImage(systemName: "chevron.left")!) { _ in change(index - 1) }) }
        if index + 1 < count { items.append(CPBarButton(image: UIImage(systemName: "chevron.right")!) { _ in change(index + 1) }) }
        page.trailingNavigationBarButtons = items
    }

    private func notice(_ message: String) {
        guard controller?.presentedTemplate == nil else { return }
        let action = CPAlertAction(title: "OK", style: .cancel) { [weak self] _ in self?.controller?.dismissTemplate(animated: true, completion: nil) }
        controller?.presentTemplate(CPAlertTemplate(titleVariants: [String(message.prefix(240))], actions: [action]), animated: true, completion: nil)
    }
}
