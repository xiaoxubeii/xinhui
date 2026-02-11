import SwiftUI

struct ContentView: View {
    @StateObject private var dashboardViewModel = DashboardViewModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        TabView {
            DashboardView(viewModel: dashboardViewModel)
                .tabItem {
                    Label("首页", systemImage: "heart.text.square")
                }

            DietView()
                .tabItem {
                    Label("营养", systemImage: "fork.knife")
                }

            ExerciseView()
                .tabItem {
                    Label("运动", systemImage: "figure.run")
                }

            DataHubView(viewModel: dashboardViewModel)
                .tabItem {
                    Label("数据", systemImage: "list.bullet.rectangle")
                }

            SettingsView()
                .tabItem {
                    Label("设置", systemImage: "gearshape")
                }
        }
        .task { dashboardViewModel.load() }
        .onChange(of: scenePhase) { _, phase in
            switch phase {
            case .active:
                dashboardViewModel.startLiveUpdates()
            case .background:
                dashboardViewModel.stopLiveUpdates()
            case .inactive:
                break
            @unknown default:
                break
            }
        }
    }
}
