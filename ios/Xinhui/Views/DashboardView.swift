import SwiftUI

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // 上次同步信息
                    if let lastSync = viewModel.lastSyncDate {
                        HStack {
                            Image(systemName: "arrow.triangle.2.circlepath")
                                .foregroundColor(.secondary)
                            Text("上次同步: \(DateFormatters.displayDateTime.string(from: lastSync))")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Spacer()
                        }
                        .padding(.horizontal)
                    }

                    NavigationLink(destination: AgentChatView()) {
                        AgentEntryCard()
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal)

                    // 指标卡片网格
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                    ], spacing: 12) {
                        MetricCard(
                            title: "今日步数",
                            value: "\(viewModel.todaySteps)",
                            unit: "步",
                            iconName: "figure.walk",
                            color: .green
                        )

                        MetricCard(
                            title: "心率",
                            value: viewModel.latestHeartRate.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "bpm",
                            iconName: "heart.fill",
                            color: .red
                        )

                        MetricCard(
                            title: "血氧",
                            value: viewModel.latestSpO2.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "%",
                            iconName: "lungs.fill",
                            color: .blue
                        )

                        MetricCard(
                            title: "昨晚睡眠",
                            value: viewModel.lastSleepHours.map { String(format: "%.1f", $0) } ?? "--",
                            unit: "小时",
                            iconName: "bed.double.fill",
                            color: .purple
                        )

                        MetricCard(
                            title: "今日摄入",
                            value: viewModel.todayIntakeKcal.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "kcal",
                            iconName: "fork.knife",
                            color: .orange
                        )

                        MetricCard(
                            title: "今日消耗",
                            value: viewModel.todayBurnedKcal.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "kcal",
                            iconName: "flame.fill",
                            color: .pink
                        )
                    }
                    .padding(.horizontal)

                    // 设备 ID
                    HStack {
                        Text("设备 ID")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Spacer()
                        Text(viewModel.deviceId.prefix(8) + "...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal)
                }
                .padding(.vertical)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("心慧智问")
            .onAppear { viewModel.load() }
            .refreshable { await viewModel.refreshTodayData() }
        }
    }
}

private struct AgentEntryCard: View {
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "sparkles")
                .font(.title3)
                .foregroundColor(.blue)
            VStack(alignment: .leading, spacing: 4) {
                Text("智问")
                    .font(.headline)
                Text("问问你的健康助理")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
            Image(systemName: "chevron.right")
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}
