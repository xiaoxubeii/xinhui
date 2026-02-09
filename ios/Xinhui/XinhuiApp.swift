import SwiftUI

@main
struct XinhuiApp: App {
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            ContentView()
                .onAppear {
                    AutoSyncManager.shared.triggerIfEnabled()
                }
                .onChange(of: scenePhase) { phase in
                    if phase == .active {
                        AutoSyncManager.shared.triggerIfEnabled()
                    }
                }
        }
    }
}
