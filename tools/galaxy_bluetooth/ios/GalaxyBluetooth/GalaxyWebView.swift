import SwiftUI
import WebKit

struct GalaxyWebView: UIViewRepresentable {
    let url: URL
    let requestKey: String

    func makeCoordinator() -> Coordinator { Coordinator(origin: url) }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        // A normal on-phone HTTP origin preserves ES modules, fetch, XHR,
        // iframes, multipart bodies and Response semantics without editing Galaxy.
        // Only requests to this same local origin receive the private header.
        let script = """
        (() => {
          window.__galaxyNative = true;
          const key = '\(requestKey)';
          const local = (u) => new URL(u, location.href).origin === location.origin;
          const originalFetch = window.fetch.bind(window);
          window.fetch = (input, init = {}) => {
            const req = new Request(input, init);
            if (!local(req.url)) return originalFetch(req);
            const headers = new Headers(req.headers);
            headers.set('X-Galaxy-Local', key);
            return originalFetch(new Request(req, { headers }));
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

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        let origin: URL
        init(origin: URL) { self.origin = origin }

        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = action.request.url else { decisionHandler(.cancel); return }
            if url.scheme == origin.scheme, url.host == origin.host, url.port == origin.port {
                decisionHandler(.allow)
            } else if url.scheme == "about" || url.scheme == "blob" {
                decisionHandler(.allow)
            } else {
                if action.navigationType == .linkActivated, ["https", "http"].contains(url.scheme ?? "") {
                    UIApplication.shared.open(url)
                }
                decisionHandler(.cancel)
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
