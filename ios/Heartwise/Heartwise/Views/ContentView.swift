import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("首页", systemImage: "heart.text.square")
                }

            DietView()
                .tabItem {
                    Label("饮食", systemImage: "fork.knife")
                }

            SyncView()
                .tabItem {
                    Label("同步", systemImage: "arrow.triangle.2.circlepath")
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
