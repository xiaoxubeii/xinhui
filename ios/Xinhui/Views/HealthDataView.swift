import SwiftUI

struct HealthDataView: View {
    @State private var selectedType: HealthDataType = .steps
    @State private var items: [String] = []
    @State private var isLoading = false

    private let healthKit = HealthKitManager()

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // 类型选择器
                Picker("数据类型", selection: $selectedType) {
                    ForEach(HealthDataType.allCases) { type in
                        Label(type.rawValue, systemImage: type.iconName).tag(type)
                    }
                }
                .pickerStyle(.segmented)
                .padding()

                if isLoading {
                    Spacer()
                    ProgressView("正在加载...")
                    Spacer()
                } else if items.isEmpty {
                    Spacer()
                    VStack(spacing: 8) {
                        Image(systemName: "tray")
                            .font(.largeTitle)
                            .foregroundColor(.secondary)
                        Text("暂无数据")
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                } else {
                    List(items, id: \.self) { item in
                        Text(item)
                            .font(.system(.body, design: .monospaced))
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("数据浏览")
            .onChange(of: selectedType) { _ in
                Task { await loadData() }
            }
            .task { await loadData() }
        }
    }

    private func loadData() async {
        isLoading = true
        defer { isLoading = false }

        guard healthKit.isAvailable else {
            items = ["HealthKit 不可用"]
            return
        }

        do {
            try await healthKit.requestAuthorization()
        } catch {
            items = ["未授权"]
            return
        }

        let end = Date()
        let start = Calendar.current.date(byAdding: .day, value: -7, to: end)!

        do {
            switch selectedType {
            case .steps:
                let data = try await healthKit.fetchDailySteps(start: start, end: end)
                items = data.map { "\($0.date)  \($0.count) 步" }
            case .heartRate:
                let data = try await healthKit.fetchHeartRateSamples(start: start, end: end)
                items = data.suffix(50).map { "\($0.timestamp)  \(String(format: "%.0f", $0.bpm)) bpm" }
            case .restingHeartRate:
                let data = try await healthKit.fetchRestingHeartRates(start: start, end: end)
                items = data.map { "\($0.date)  \(String(format: "%.0f", $0.bpm)) bpm" }
            case .spo2:
                let data = try await healthKit.fetchSpO2Readings(start: start, end: end)
                items = data.suffix(50).map { "\($0.timestamp)  \(String(format: "%.1f", $0.percentage))%" }
            case .sleep:
                let data = try await healthKit.fetchSleepSessions(start: start, end: end)
                items = data.map { "\($0.stage)  \($0.startTime) → \($0.endTime)" }
            case .workouts:
                let data = try await healthKit.fetchWorkouts(start: start, end: end)
                items = data.map {
                    let mins = Int($0.durationSeconds / 60)
                    return "\($0.activityType)  \(mins)分钟  \($0.startTime)"
                }
            }
        } catch {
            items = ["加载失败: \(error.localizedDescription)"]
        }
    }
}
