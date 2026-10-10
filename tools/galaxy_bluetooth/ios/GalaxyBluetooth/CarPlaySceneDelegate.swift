import CarPlay

@MainActor
final class CarPlaySceneDelegate: NSObject, CPTemplateApplicationSceneDelegate {
    private var controller: CPInterfaceController?
    private var template: CPListTemplate?
    private var timer: Timer?

    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didConnect interfaceController: CPInterfaceController) {
        controller = interfaceController
        let root = CPListTemplate(title: "StarPilot", sections: [])
        template = root
        interfaceController.setRootTemplate(root, animated: false, completion: nil)
        let model = AppModel.shared
        model.setCarPlayActive(true)
        model.diagnostics.live = true
        model.showDiagnostics = true
        refresh()
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refresh() }
        }
    }
    func templateApplicationScene(_ scene: CPTemplateApplicationScene, didDisconnectInterfaceController interfaceController: CPInterfaceController) {
        timer?.invalidate(); timer = nil; controller = nil; template = nil
        AppModel.shared.setCarPlayActive(false)
    }
    private func refresh() {
        let model = AppModel.shared
        let diagnostics = model.diagnostics
        var sections = [CPListSection(items: [CPListItem(text: diagnostics.fresh ? model.transport.label : "Disconnected / outdated",
                                                      detailText: diagnostics.fresh ? "Live View selected on iPhone" : diagnostics.status)])]
        if diagnostics.fresh, let sample = diagnostics.snapshot {
            sections.append(CPListSection(items: [CPListItem(text: "Driving status", detailText: sample.engaged.map { $0 ? "Engaged" : "Not engaged" } ?? "Not reported")]))
            sections.append(CPListSection(items: sample.temperatures.map { CPListItem(text: $0.name, detailText: $0.display) }, header: "Temperatures", sectionIndexTitle: nil))
            sections.append(CPListSection(items: sample.rates.map { CPListItem(text: $0.name, detailText: $0.display) }, header: "Frame / message rates", sectionIndexTitle: nil))
        }
        template?.updateSections(sections)
    }
}
