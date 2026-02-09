import SwiftUI

struct SettingsView: View {
    @StateObject private var viewModel = SettingsViewModel()

    var body: some View {
        NavigationView {
            Form {
                Section("服务器") {
                    TextField("API 地址", text: $viewModel.serverURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        .onSubmit { viewModel.saveServerURL() }

                    Button("保存") { viewModel.saveServerURL() }
                }

                Section("设备信息") {
                    LabeledContent("设备 ID", value: viewModel.deviceId)
                    LabeledContent("HealthKit", value: viewModel.healthKitAvailable ? "可用" : "不可用")
                }

                Section("数据权限") {
                    if viewModel.permissionStatuses.isEmpty {
                        Text("无权限信息")
                            .foregroundColor(.secondary)
                    } else {
                        ForEach(viewModel.permissionStatuses, id: \.name) { item in
                            PermissionRow(name: item.name, granted: item.granted)
                        }
                    }

                    Button("刷新权限状态") {
                        viewModel.refreshPermissions()
                    }
                }

                Section("关于") {
                    LabeledContent("版本", value: "1.0.0")
                    LabeledContent("应用", value: "心慧智问")
                }
            }
            .navigationTitle("设置")
            .onAppear { viewModel.load() }
        }
    }
}
