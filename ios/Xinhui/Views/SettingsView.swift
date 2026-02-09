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

                Section("登录") {
                    TextField("邮箱", text: $viewModel.loginEmail)
                        .keyboardType(.emailAddress)
                        .textContentType(.emailAddress)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)

                    SecureField("密码", text: $viewModel.loginPassword)
                        .textContentType(.password)

                    Button {
                        Task { await viewModel.loginAndCreateApiKey() }
                    } label: {
                        if viewModel.isAuthBusy {
                            HStack {
                                ProgressView()
                                Text("登录中…")
                            }
                        } else {
                            Text("登录并创建 API Key")
                        }
                    }
                    .disabled(viewModel.isAuthBusy)

                    if !viewModel.authStatus.isEmpty {
                        Text(viewModel.authStatus)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    if !viewModel.authError.isEmpty {
                        Text("失败: \(viewModel.authError)")
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }

                Section("API Key") {
                    LabeledContent("当前", value: viewModel.apiKeyMasked)
                    Button("清除 API Key") {
                        viewModel.clearApiKey()
                    }
                    .disabled(viewModel.apiKey.isEmpty)
                }

                Section("同步") {
                    Toggle("打开 App 自动同步", isOn: $viewModel.autoSyncEnabled)
                        .onChange(of: viewModel.autoSyncEnabled) { isOn in
                            viewModel.saveAutoSyncEnabled()
                            if isOn {
                                AutoSyncManager.shared.triggerIfEnabled(force: true)
                            }
                            viewModel.refreshAutoSyncStatus()
                        }

                    Text("开启后，每次打开 App 会自动同步最近 \(Constants.autoSyncDays) 天健康数据到服务器。首次可能会弹出 HealthKit 授权。")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    LabeledContent("上次尝试", value: viewModel.lastAutoSyncAttemptText)
                    LabeledContent("上次成功", value: viewModel.lastAutoSyncSuccessText)
                    if !viewModel.lastAutoSyncError.isEmpty {
                        Text("上次错误: \(viewModel.lastAutoSyncError)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
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
