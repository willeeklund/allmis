import SwiftUI

struct ContentView: View {
    static let siteURL = URL(string: "https://willeeklund.github.io/allmis/")!
    static let reloadAfter: TimeInterval = 30 * 60

    @Environment(\.scenePhase) private var scenePhase
    @State private var failed = false
    @State private var reloadToken = 0
    @State private var backgroundedAt: Date?

    var body: some View {
        ZStack {
            Color("PageBackground").ignoresSafeArea()
            AllmisWebView(url: Self.siteURL, reloadToken: reloadToken, failed: $failed)
            if failed {
                offline
            }
        }
        .onChange(of: scenePhase) { _, phase in
            switch phase {
            case .background:
                backgroundedAt = Date()
            case .active:
                if let backgroundedAt, Date().timeIntervalSince(backgroundedAt) > Self.reloadAfter {
                    reloadToken += 1
                }
                backgroundedAt = nil
            default:
                break
            }
        }
    }

    private var offline: some View {
        VStack(spacing: 16) {
            Text("🙈").font(.system(size: 64))
            Text("Kunde inte ladda schemat")
                .font(.title2.bold())
            Text("Kolla att du har internet och prova igen.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Prova igen") {
                failed = false
                reloadToken += 1
            }
            .buttonStyle(.borderedProminent)
            .tint(Color("AccentColor"))
            .controlSize(.large)
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color("PageBackground"))
    }
}

#Preview {
    ContentView()
}
