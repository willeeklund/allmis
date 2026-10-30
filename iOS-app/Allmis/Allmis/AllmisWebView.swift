import SwiftUI
import WebKit

struct AllmisWebView {
    let url: URL
    let reloadToken: Int
    @Binding var failed: Bool

    func makeCoordinator() -> Coordinator {
        Coordinator(url: url, failed: $failed)
    }

    private func makeWebView(coordinator: Coordinator) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.limitsNavigationsToAppBoundDomains = true
        config.websiteDataStore = .default()

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = coordinator
        webView.allowsBackForwardNavigationGestures = false
        #if DEBUG
        if #available(iOS 16.4, macOS 13.3, *) {
            webView.isInspectable = true
        }
        #endif
        coordinator.webView = webView
        coordinator.lastReloadToken = reloadToken
        webView.load(URLRequest(url: url))
        return webView
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        let url: URL
        @Binding var failed: Bool
        weak var webView: WKWebView?
        var lastReloadToken = 0

        init(url: URL, failed: Binding<Bool>) {
            self.url = url
            _failed = failed
        }

        func reload() {
            guard let webView else { return }
            if webView.url == nil {
                webView.load(URLRequest(url: url))
            } else {
                webView.reload()
            }
        }

        func reloadIfNeeded(token: Int) {
            guard token != lastReloadToken else { return }
            lastReloadToken = token
            reload()
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction) async -> WKNavigationActionPolicy {
            guard let target = navigationAction.request.url,
                  let scheme = target.scheme, ["http", "https"].contains(scheme),
                  target.host != url.host
            else { return .allow }
            openExternally(target)
            return .cancel
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            failed = false
            endRefreshing()
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            handle(error)
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            handle(error)
        }

        private func handle(_ error: Error) {
            endRefreshing()
            if (error as NSError).code == NSURLErrorCancelled { return }
            failed = true
        }

        private func openExternally(_ target: URL) {
            #if os(macOS)
            NSWorkspace.shared.open(target)
            #else
            UIApplication.shared.open(target)
            #endif
        }

        private func endRefreshing() {
            #if !os(macOS)
            webView?.scrollView.refreshControl?.endRefreshing()
            #endif
        }

        #if !os(macOS)
        @objc func pullToRefresh(_ sender: UIRefreshControl) {
            reload()
        }
        #endif
    }
}

#if os(macOS)
extension AllmisWebView: NSViewRepresentable {
    func makeNSView(context: Context) -> WKWebView {
        let webView = makeWebView(coordinator: context.coordinator)
        webView.setValue(false, forKey: "drawsBackground")
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        context.coordinator.reloadIfNeeded(token: reloadToken)
    }
}
#else
extension AllmisWebView: UIViewRepresentable {
    func makeUIView(context: Context) -> WKWebView {
        let webView = makeWebView(coordinator: context.coordinator)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        let refresh = UIRefreshControl()
        refresh.addTarget(context.coordinator, action: #selector(Coordinator.pullToRefresh(_:)), for: .valueChanged)
        webView.scrollView.refreshControl = refresh
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.reloadIfNeeded(token: reloadToken)
    }
}
#endif
