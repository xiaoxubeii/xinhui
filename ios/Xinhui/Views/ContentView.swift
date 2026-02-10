import SwiftUI

struct ContentView: View {
    @StateObject private var dashboardViewModel = DashboardViewModel()

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

            HealthDataView()
                .tabItem {
                    Label("数据", systemImage: "list.bullet.rectangle")
                }

            SettingsView()
                .tabItem {
                    Label("设置", systemImage: "gearshape")
                }
        }
    }
}
