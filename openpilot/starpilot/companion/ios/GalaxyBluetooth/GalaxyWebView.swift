import SwiftUI
import WebKit

private struct GalaxyDownloadedFile: Identifiable {
    let id = UUID()
    let url: URL
}

@MainActor
final class GalaxyPageDiagnostics: ObservableObject {
    @Published fileprivate var downloadedFile: GalaxyDownloadedFile?
    @Published var downloadError: String?
    private var exportDirectory: URL?

    fileprivate func offerDownload(_ url: URL) {
        exportDirectory = url.deletingLastPathComponent()
        downloadedFile = GalaxyDownloadedFile(url: url)
        record("Download ready to save or share")
    }
    func cleanUpDownload() {
        if let directory = exportDirectory { try? FileManager.default.removeItem(at: directory) }
        exportDirectory = nil
    }
    func downloadFailed(_ error: Error) {
        let value = error as NSError
        record("Download failed: \(value.domain) \(value.code)")
        downloadError = "The file couldn’t be downloaded. Please try again."
    }

    var recover: ((Bool) -> Void)?
    @Published var darkAppearance: Bool?
    @Published var landscapeEditor = false
    @Published var copied = false
    @Published var stalled = false
    @Published var mounted = false
    @Published var reloadID = UUID()
    private(set) var started = Date()
    private(set) var events: [String] = []
    private var deadline: Task<Void, Never>?

    func record(_ event: String) {
        events.append("\(ISO8601DateFormatter().string(from: Date())) \(event.prefix(300))")
        if events.count > 40 { events.removeFirst(events.count - 40) }
    }
    func begin() {
        deadline?.cancel()
        started = Date(); mounted = false; stalled = false; landscapeEditor = false
        record("Page loading")
        deadline = Task { [weak self] in
            do { try await Task.sleep(nanoseconds: 12_000_000_000) } catch { return }
            guard let self, !self.mounted else { return }
            self.record("No rendered Galaxy content after 12 seconds")
            self.stalled = true
        }
    }
    func rendered() {
        mounted = true; stalled = false; deadline?.cancel()
        record("Galaxy content rendered")
    }
    func fail(_ event: String) { record(event); mounted = false; stalled = true; deadline?.cancel() }
    func retry() { reloadID = UUID() }
    func report(server: LoopbackServer, connection: String) -> String {
        let info = Bundle.main.infoDictionary ?? [:]
        return """
        StarPilot BT Galaxy diagnostics
        \(ISO8601DateFormatter().string(from: Date()))
        App: \(info["CFBundleShortVersionString"] ?? "?") (\(info["CFBundleVersion"] ?? "?"))
        iOS: \(UIDevice.current.systemVersion)
        Connection: \(connection)
        Galaxy content rendered: \(mounted)
        Page age: \(Int(Date().timeIntervalSince(started))) seconds
        \(server.diagnosticSummary)
        Recent page events:
        \(events.joined(separator: "\n"))
        Recent local requests (no headers, query values or bodies):
        \(server.recentRequests.joined(separator: "\n"))
        """
    }
}

struct GalaxyWebView: View {
    let url: URL
    let requestKey: String
    @ObservedObject var diagnostics: GalaxyPageDiagnostics
    var isActive = true
    let report: () -> String
    var body: some View {
        ZStack {
            GalaxyPage(url: url, requestKey: requestKey, diagnostics: diagnostics, isActive: isActive)
                .id(url.absoluteString + diagnostics.reloadID.uuidString)
            if diagnostics.stalled {
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.bubble").font(.largeTitle).foregroundStyle(.purple)
                    Text("Galaxy hasn’t loaded").font(.title2.bold())
                    Text("Copy the report so we can find what failed, or try loading the page again.")
                        .foregroundStyle(.secondary).multilineTextAlignment(.center)
                    Button(diagnostics.copied ? "Report copied" : "Copy error report") {
                        UIPasteboard.general.string = report(); diagnostics.copied = true
                    }.buttonStyle(.borderedProminent).tint(.purple)
                    Button("Retry Galaxy") { diagnostics.copied = false; diagnostics.recover?(false) }.buttonStyle(.bordered)
                }.padding(28).frame(maxWidth: 420)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20)).padding(20)
            }
        }
        .sheet(item: $diagnostics.downloadedFile, onDismiss: diagnostics.cleanUpDownload) { file in
            GalaxyFileShareSheet(url: file.url) { diagnostics.downloadedFile = nil }
        }
        .alert("Couldn’t download file", isPresented: Binding(
            get: { diagnostics.downloadError != nil },
            set: { if !$0 { diagnostics.downloadError = nil } }
        )) {
            Button("OK", role: .cancel) { diagnostics.downloadError = nil }
        } message: { Text(diagnostics.downloadError ?? "") }
    }
}

private struct GalaxyFileShareSheet: UIViewControllerRepresentable {
    let url: URL
    let finished: () -> Void
    func makeUIViewController(context: Context) -> UIActivityViewController {
        let controller = UIActivityViewController(activityItems: [url], applicationActivities: nil)
        controller.completionWithItemsHandler = { _, _, _, _ in
            Task { @MainActor in finished() }
        }
        return controller
    }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) {}
}

private struct GalaxyPage: UIViewRepresentable {
    let url: URL
    let requestKey: String

    let diagnostics: GalaxyPageDiagnostics
    let isActive: Bool
    func makeCoordinator() -> Coordinator {
        let coordinator = Coordinator(origin: url, diagnostics: diagnostics)
        coordinator.isVisible = isActive
        return coordinator
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        diagnostics.begin()
        config.userContentController.add(context.coordinator, name: "galaxyDiagnostics")
        let script = """
        (() => {
          if (location.origin !== '\(url.scheme!)://\(url.host!):\(url.port!)') return;
          window.__galaxyNative = true;
          const phoneAppearance = window.matchMedia('(prefers-color-scheme: dark)');
          const syncTheme = () => {
            const theme = phoneAppearance.matches ? 'dark' : 'light';
            localStorage.setItem('galaxy-preview-theme', theme);
            document.documentElement.dataset.theme = theme;
          };
          syncTheme();
          phoneAppearance.addEventListener('change', () => {
            const dark = phoneAppearance.matches;
            if ((document.documentElement.dataset.theme === 'dark') !== dark) {
              document.querySelector('.gx-theme-toggle')?.click();
            }
            syncTheme();
          });
          const reportTheme = () => {
            const theme = document.documentElement?.dataset.theme;
            if (theme !== 'dark' && theme !== 'light') return;
            try { window.webkit.messageHandlers.galaxyDiagnostics.postMessage({kind: 'theme', dark: theme === 'dark'}); } catch (_) {}
          };
          const watchTheme = () => {
            if (!document.documentElement) return;
            new MutationObserver(reportTheme).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
            reportTheme();
          };
          if (document.documentElement) watchTheme();
          else document.addEventListener('DOMContentLoaded', watchTheme, {once: true});
          let nativeVisible = \(isActive ? "true" : "false");
          Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => nativeVisible ? 'visible' : 'hidden'});
          Object.defineProperty(document, 'hidden', {configurable: true, get: () => !nativeVisible});
          window.__galaxySetVisible = visible => {
            if (nativeVisible === !!visible) return;
            nativeVisible = !!visible;
            document.dispatchEvent(new Event('visibilitychange'));
          };
          const emit = (kind, path = '', code = 0) => {
            try { window.webkit.messageHandlers.galaxyDiagnostics.postMessage({kind, path, code}); } catch (_) {}
          };
          // Keep this native presentation independent of downloaded Galaxy assets.
          const editorScreen = matchMedia('(orientation: landscape) and (max-height: 600px)');
          let editorFocused = false;
          const editorCSS = document.createElement('style');
          editorCSS.textContent = `
            html.native-layout-editor .blur-nav,
            html.native-layout-editor .gx-appbar__pill,
            html.native-layout-editor .gx-appbar__menu,
            html.native-layout-editor .gx-layout > .gx-page-header { display: none !important; }
            html.native-layout-editor .gx-app { animation: none; }
            html.native-layout-editor .gx-appbar {
              position: fixed; inset: max(4px, env(safe-area-inset-top)) auto auto max(8px, env(safe-area-inset-left));
              width: 44px; padding: 0; margin: 0; z-index: 20;
            }
            html.native-layout-editor .gx-appbar__back { width: 44px; height: 44px; min-width: 44px; min-height: 44px; }
            html.native-layout-editor .gx-content {
              max-width: none; padding: max(4px, env(safe-area-inset-top)) max(8px, env(safe-area-inset-right)) max(8px, env(safe-area-inset-bottom)) max(8px, env(safe-area-inset-left));
            }
            html.native-layout-editor .gx-layout { --layout-sticky-top: max(4px, env(safe-area-inset-top)); display: grid; gap: 6px; }
            html.native-layout-editor .gx-layout__savebar {
              grid-row: 1; margin-left: 52px; padding: 0 4px 0 10px; min-height: 44px; gap: 4px;
            }
            html.native-layout-editor .gx-layout__savebar .gx-btn { min-height: 44px; padding-inline: 12px; }
            html.native-layout-editor .gx-layout__targets { grid-row: 2; margin: 0; gap: 8px; }
            html.native-layout-editor .gx-layout__targets .gx-btn { min-height: 44px; padding: 4px 12px; }
            html.native-layout-editor .gx-layout__workspace { gap: 8px; grid-template-columns: minmax(0, 1.35fr) minmax(260px, 1fr); }
            html.native-layout-editor .gx-layout__preview-card { padding: 4px; gap: 4px; }
            html.native-layout-editor .gx-layout__preview-card > p.gx-note:not([role]) { display: none; }
            html.native-layout-editor .gx-layout__preview-card .gx-layout__preview {
              width: auto; max-width: 100%; max-height: calc(100svh - 200px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); margin-inline: auto;
            }
            html.native-layout-editor .gx-layout__inspector {
              padding: 8px; gap: 8px; max-height: calc(100svh - 124px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); overflow: auto;
            }
            html.native-layout-editor .gx-layout__sections { margin: -8px -8px 0; padding: 4px; gap: 2px; top: -8px; }
            html.native-layout-editor .gx-layout__sections .gx-btn { min-height: 44px; padding: 4px 8px; white-space: nowrap; }
          `;
          const syncEditor = () => {
            const focused = editorScreen.matches && !!document.querySelector('.gx-layout');
            if (focused === editorFocused) return;
            editorFocused = focused;
            document.documentElement.classList.toggle('native-layout-editor', focused);
            try { window.webkit.messageHandlers.galaxyDiagnostics.postMessage({kind: 'editorFocus', active: focused}); } catch (_) {}
          };
          const startEditorPresentation = () => {
            document.head.appendChild(editorCSS);
            new MutationObserver(syncEditor).observe(document.body, {childList: true, subtree: true});
            editorScreen.addEventListener('change', syncEditor);
            syncEditor();
          };
          document.addEventListener('DOMContentLoaded', startEditorPresentation, {once: true});
          const pathOnly = value => {
            try { return new URL(value, location.href).pathname; } catch (_) { return ''; }
          };
          window.addEventListener('error', event => {
            if (event.target && event.target !== window) {
              emit('resource', pathOnly(event.target.src || event.target.href || ''));
            } else { emit('script', pathOnly(event.filename || ''), event.lineno || 0); }
          }, true);
          window.addEventListener('unhandledrejection', () => emit('promise'));
          let rendered = false;
          const checkContent = () => {
            const root = document.querySelector('#galaxy-app');
            if (root && !root.hasAttribute('v-cloak') && root.children.length && root.innerText.trim().length) {
              if (!rendered) { rendered = true; emit('rendered'); }
            } else if (rendered) { rendered = false; emit('blank'); }
          };
          window.addEventListener('DOMContentLoaded', () => {
            checkContent(); setInterval(checkContent, 1000);
          }, {once: true});
          const key = '\(requestKey)';
          const local = (u) => new URL(u, location.href).origin === location.origin;
          const originalFetch = window.fetch.bind(window);
          window.fetch = (input, init = {}) => {
            const req = new Request(input, init);
            if (!local(req.url)) return originalFetch(req);
            const headers = new Headers(req.headers);
            headers.set('X-Galaxy-Local', key);
            return originalFetch(new Request(req, { headers })).then(async response => {
              if (response.status === 501) {
                const message = await response.clone().json().catch(() => null);
                let notice = document.getElementById('native-wifi-notice');
                if (!notice) {
                  notice = document.createElement('button'); notice.id = 'native-wifi-notice';
                  notice.setAttribute('role', 'status');
                  notice.style.cssText = 'position:fixed;top:12px;left:12px;right:12px;z-index:10000;padding:16px;border-radius:16px;background:Canvas;color:CanvasText;border:1px solid currentColor;font:inherit;';
                  notice.onclick = () => notice.remove(); document.body.appendChild(notice);
                }
                notice.textContent = typeof message?.error === 'string' ? message.error : 'Connect to comma over Wi-Fi for this feature.';
              }
              return response;
            });
          };
          const originalOpen = XMLHttpRequest.prototype.open;
          const originalSend = XMLHttpRequest.prototype.send;
          XMLHttpRequest.prototype.open = function(method, url, ...rest) {
            this.__galaxyLocal = local(url);
            return originalOpen.call(this, method, url, ...rest);
          };
          XMLHttpRequest.prototype.send = function(body) {
            if (this.__galaxyLocal) this.setRequestHeader('X-Galaxy-Local', key);
            return originalSend.call(this, body);
          };
        })();
        """
        config.userContentController.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: false))
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.06, green: 0.05, blue: 0.09, alpha: 1)
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        context.coordinator.isVisible = isActive
        context.coordinator.syncVisibility(uiView)
    }
    static func dismantleUIView(_ uiView: WKWebView, coordinator: Coordinator) {
        uiView.configuration.userContentController.removeScriptMessageHandler(forName: "galaxyDiagnostics")
        uiView.navigationDelegate = nil; uiView.uiDelegate = nil
        coordinator.cancelDownloads()
        uiView.stopLoading()
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler, WKDownloadDelegate {
        private var downloads: [ObjectIdentifier: (WKDownload, URL?)] = [:]
        var isVisible = true
        func syncVisibility(_ webView: WKWebView) {
            webView.evaluateJavaScript("window.__galaxySetVisible?.(\(isVisible ? "true" : "false"))", completionHandler: nil)
        }
        let origin: URL
        let diagnostics: GalaxyPageDiagnostics
        init(origin: URL, diagnostics: GalaxyPageDiagnostics) { self.origin = origin; self.diagnostics = diagnostics }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            let frame = message.frameInfo.securityOrigin
            guard frame.protocol == origin.scheme, frame.host == origin.host, frame.port == origin.port,
                  let body = message.body as? [String: Any], let kind = body["kind"] as? String else { return }
            let path = LoopbackServer.reportPath(body["path"] as? String ?? "")
            switch kind {
            case "theme":
                if message.frameInfo.isMainFrame, let dark = body["dark"] as? Bool {
                    diagnostics.darkAppearance = dark
                    let background = dark ? UIColor(red: 0.06, green: 0.05, blue: 0.09, alpha: 1) : .systemBackground
                    message.webView?.backgroundColor = background
                    message.webView?.scrollView.backgroundColor = background
                }
            case "editorFocus":
                if message.frameInfo.isMainFrame, let active = body["active"] as? Bool {
                    diagnostics.landscapeEditor = active
                }
            case "rendered": if message.frameInfo.isMainFrame { diagnostics.rendered() }
            case "blank": if message.frameInfo.isMainFrame { diagnostics.begin() }
            case "resource": diagnostics.record("Resource failed: \(path)")
            case "script": diagnostics.record("JavaScript error: \(path), line \(body["code"] as? Int ?? 0)")
            case "promise": diagnostics.record("Unhandled JavaScript promise rejection")
            case "search":
                if let phase = body["phase"] as? String, ["started", "results", "partial", "ready"].contains(phase),
                   let count = body["count"] as? Int, (0...50_000).contains(count) {
                    diagnostics.record("Toggle search \(phase): \(count) settings indexed")
                }
            default: break
            }
        }
        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            syncVisibility(webView)
            diagnostics.record("HTML navigation finished; waiting for Galaxy content")
        }
        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            navigationFailed(error)
        }
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { navigationFailed(error) }
        private func navigationFailed(_ error: Error) {
            let value = error as NSError
            if !downloads.isEmpty, value.code == NSURLErrorCancelled || (value.domain == "WKErrorDomain" && value.code == 102) { return }
            if value.domain == NSURLErrorDomain && value.code == NSURLErrorCancelled { return }
            diagnostics.fail("Navigation failed: \(value.domain) \(value.code)")
            if isVisible, value.domain == NSURLErrorDomain,
               [NSURLErrorCannotConnectToHost, NSURLErrorNetworkConnectionLost].contains(value.code) {
                diagnostics.recover?(true)
            }
        }
        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            diagnostics.fail("Galaxy web content process terminated")
            if isVisible { diagnostics.recover?(true) }
        }


        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = action.request.url else { decisionHandler(.cancel); return }
            if url.scheme == origin.scheme, url.host == origin.host, url.port == origin.port {
                decisionHandler(action.shouldPerformDownload ? .download : .allow)
            } else if url.scheme == "blob" {
                let frame = action.sourceFrame.securityOrigin
                guard frame.protocol == origin.scheme, frame.host == origin.host,
                      frame.port == origin.port else { decisionHandler(.cancel); return }
                decisionHandler(action.shouldPerformDownload ? .download : .allow)
            } else if url.scheme == "about" {
                decisionHandler(.allow)
            } else {
                if action.navigationType == .linkActivated, ["https", "http"].contains(url.scheme ?? "") {
                    UIApplication.shared.open(url)
                }
                decisionHandler(.cancel)
            }
        }

        func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
            track(download)
        }
        func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
            track(download)
        }
        private func track(_ download: WKDownload) {
            guard downloads.isEmpty, diagnostics.downloadedFile == nil else {
                download.cancel { _ in }
                return
            }
            downloads[ObjectIdentifier(download)] = (download, nil)
            download.delegate = self
            diagnostics.record("File download started")
        }
        func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                      suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
            let id = ObjectIdentifier(download)
            guard downloads[id] != nil else { completionHandler(nil); return }
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
            do {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                let name = (suggestedFilename as NSString).lastPathComponent
                let safeName = name.isEmpty || name == "." || name == ".." ? "toggle-backup.json" : name
                let destination = directory.appendingPathComponent(safeName)
                downloads[id] = (download, destination)
                completionHandler(destination)
            } catch {
                try? FileManager.default.removeItem(at: directory)
                completionHandler(nil)
                diagnostics.downloadFailed(error)
            }
        }
        func downloadDidFinish(_ download: WKDownload) {
            guard let (_, destination) = downloads.removeValue(forKey: ObjectIdentifier(download)),
                  let destination else { return }
            diagnostics.offerDownload(destination)
        }
        func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
            if let (_, destination) = downloads.removeValue(forKey: ObjectIdentifier(download)),
               let destination {
                try? FileManager.default.removeItem(at: destination.deletingLastPathComponent())
            }
            diagnostics.downloadFailed(error)
        }
        func cancelDownloads() {
            let active = downloads.values
            downloads.removeAll()
            for (download, destination) in active {
                download.delegate = nil
                download.cancel { _ in }
                if let destination { try? FileManager.default.removeItem(at: destination.deletingLastPathComponent()) }
            }
        }

        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                     for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
            if action.targetFrame == nil, let url = action.request.url, ["https", "http"].contains(url.scheme ?? "") {
                UIApplication.shared.open(url)
            }
            return nil
        }
    }
}
