import SwiftUI

struct SyncView: View {
    @StateObject private var viewModel = SyncViewModel()

    var body: some View {
        Form {
            // 日期范围
            Section("同步范围") {
                DatePicker("开始日期", selection: $viewModel.startDate, displayedComponents: .date)
                DatePicker("结束日期", selection: $viewModel.endDate, displayedComponents: .date)
            }

            // 数据类型选择
            Section("数据类型") {
                ForEach(HealthDataType.allCases) { type in
                    Toggle(isOn: Binding(
                        get: { viewModel.selectedTypes.contains(type) },
                        set: { isOn in
                            if isOn { viewModel.selectedTypes.insert(type) }
                            else { viewModel.selectedTypes.remove(type) }
                        }
                    )) {
                        Label(type.rawValue, systemImage: type.iconName)
                    }
                }
            }

            // 同步按钮 + 进度
            Section {
                if viewModel.isSyncing {
                    SyncProgressView(progress: viewModel.progress)
                } else {
                    Button(action: { viewModel.startSync() }) {
                        HStack {
                            Spacer()
                            Image(systemName: "arrow.up.circle.fill")
                            Text("开始同步")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                    .disabled(viewModel.selectedTypes.isEmpty)
                }
            }

            // 结果
            if let response = viewModel.lastResponse {
                Section("同步结果") {
                    LabeledContent("状态", value: response.status)
                    LabeledContent("消息", value: response.message)
                    ForEach(response.receivedCounts.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                        LabeledContent(key, value: "\(value)")
                    }
                }
            }
        }
        .navigationTitle("数据同步")
        .alert(
            "同步失败",
            isPresented: Binding(
                get: { viewModel.currentError != nil },
                set: { if !$0 { viewModel.currentError = nil } }
            ),
            presenting: viewModel.currentError
        ) { _ in
            Button("确定", role: .cancel) {}
        } message: { error in
            Text(error.errorDescription ?? "未知错误")
        }
    }
}
