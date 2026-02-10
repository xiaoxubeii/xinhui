import SwiftUI

struct DashboardView: View {
    @StateObject private var viewModel = DashboardViewModel()
    @State private var selectedTrend: TrendRange = .days7

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

                    if !viewModel.dashboardError.isEmpty {
                        Text(viewModel.dashboardError)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .padding(.horizontal)
                    }

                    if let balanceCard = BalanceCardData.from(viewModel: viewModel) {
                        BalanceCard(data: balanceCard)
                            .padding(.horizontal)
                    }

                    if let targets = viewModel.targets {
                        TargetsSection(targets: targets, viewModel: viewModel)
                            .padding(.horizontal)
                    }

                    TrendSection(
                        selectedTrend: $selectedTrend,
                        trend7d: viewModel.trend7d,
                        trend30d: viewModel.trend30d
                    )
                    .padding(.horizontal)

                    PlanCompletionSection(
                        exerciseItems: PlanProgressBuilder.exerciseItems(
                            plan: viewModel.exercisePlan,
                            todaySteps: viewModel.todaySteps,
                            workoutMinutes: viewModel.todayWorkoutMinutes,
                            burnedKcal: viewModel.todayBurnedKcal
                        ),
                        nutritionItems: PlanProgressBuilder.nutritionItems(
                            plan: viewModel.nutritionPlan,
                            totals: viewModel.todayNutritionTotals
                        ),
                        hasExercisePlan: viewModel.exercisePlan != nil,
                        hasNutritionPlan: viewModel.nutritionPlan != nil
                    )
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

private enum TrendRange: String, CaseIterable, Identifiable {
    case days7 = "近7天"
    case days30 = "近30天"

    var id: String { rawValue }
}

private struct BalanceCardData {
    let delta: Double
    let weeklyAvg: Double?
    let targetDelta: Double?

    static func from(viewModel: DashboardViewModel) -> BalanceCardData? {
        if let balance = viewModel.energyBalance, let delta = balance.deltaKcal {
            return BalanceCardData(delta: delta, weeklyAvg: balance.weeklyAvgKcal, targetDelta: balance.targetDeltaKcal)
        }
        guard let intake = viewModel.todayIntakeKcal, let burned = viewModel.todayBurnedKcal else { return nil }
        return BalanceCardData(delta: intake - burned, weeklyAvg: nil, targetDelta: viewModel.targets?.energyDeltaTarget)
    }
}

private struct BalanceCard: View {
    let data: BalanceCardData

    private var deltaText: String {
        String(format: "%.0f", data.delta)
    }

    private var deltaColor: Color {
        data.delta >= 0 ? .orange : .green
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "equal.circle.fill")
                    .foregroundColor(deltaColor)
                Text("能量平衡")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(deltaText)
                    .font(.title2)
                    .fontWeight(.semibold)
                    .foregroundColor(deltaColor)
                Text("kcal")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            if let weeklyAvg = data.weeklyAvg {
                Text("近7日均值：\(String(format: "%.0f", weeklyAvg)) kcal")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            if let target = data.targetDelta {
                Text("目标差：\(String(format: "%.0f", target)) kcal")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}

private struct TargetsSection: View {
    let targets: HealthTargets
    let viewModel: DashboardViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("目标进度")
                .font(.headline)
            if let target = targets.stepsTarget, target > 0 {
                TargetProgressRow(title: "步数", current: Double(viewModel.todaySteps), target: Double(target), unit: "步")
            }
            if let target = targets.sleepHoursTarget, target > 0, let current = viewModel.lastSleepHours {
                TargetProgressRow(title: "睡眠", current: current, target: target, unit: "小时")
            }
            if let target = targets.intakeKcalTarget, target > 0, let current = viewModel.todayIntakeKcal {
                TargetProgressRow(title: "摄入", current: current, target: target, unit: "kcal")
            }
            if let target = targets.burnedKcalTarget, target > 0, let current = viewModel.todayBurnedKcal {
                TargetProgressRow(title: "消耗", current: current, target: target, unit: "kcal")
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}

private struct TargetProgressRow: View {
    let title: String
    let current: Double
    let target: Double
    let unit: String

    private var progress: Double {
        guard target > 0 else { return 0 }
        return min(current / target, 1.0)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(title)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                Text(String(format: "%.0f / %.0f %@", current, target, unit))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            ProgressView(value: progress)
        }
    }
}

private struct TrendSection: View {
    @Binding var selectedTrend: TrendRange
    let trend7d: [DashboardTrendPoint]
    let trend30d: [DashboardTrendPoint]

    private var selectedData: [DashboardTrendPoint] {
        switch selectedTrend {
        case .days7: return trend7d
        case .days30: return trend30d
        }
    }

    private var maxSteps: Double {
        Double(selectedData.compactMap { $0.steps }.max() ?? 0)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("趋势")
                    .font(.headline)
                Spacer()
                Picker("趋势范围", selection: $selectedTrend) {
                    ForEach(TrendRange.allCases) { range in
                        Text(range.rawValue).tag(range)
                    }
                }
                .pickerStyle(.segmented)
            }
            if selectedData.isEmpty {
                Text("暂无趋势数据")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                VStack(spacing: 8) {
                    ForEach(selectedData) { point in
                        TrendRow(point: point, maxSteps: maxSteps)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}

private struct TrendRow: View {
    let point: DashboardTrendPoint
    let maxSteps: Double

    private var dateText: String {
        if let date = DateFormatters.dateOnly.date(from: point.date) {
            return DateFormatters.displayDate.string(from: date)
        }
        return point.date
    }

    private var stepValue: Double {
        Double(point.steps ?? 0)
    }

    private var stepRatio: Double {
        guard maxSteps > 0 else { return 0 }
        return stepValue / maxSteps
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(dateText)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
                Text("\(point.steps ?? 0) 步")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            GeometryReader { proxy in
                Capsule()
                    .fill(Color.green.opacity(0.2))
                    .frame(height: 6)
                    .overlay(
                        Capsule()
                            .fill(Color.green)
                            .frame(width: proxy.size.width * stepRatio, height: 6),
                        alignment: .leading
                    )
            }
            .frame(height: 6)
            HStack(spacing: 12) {
                if let sleep = point.sleepHours {
                    Text(String(format: "睡眠 %.1f 小时", sleep))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                if let intake = point.intakeKcal {
                    Text(String(format: "摄入 %.0f kcal", intake))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
                if let burned = point.burnedKcal {
                    Text(String(format: "消耗 %.0f kcal", burned))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
        }
    }
}

private struct PlanCompletionSection: View {
    let exerciseItems: [PlanProgressItem]
    let nutritionItems: [PlanProgressItem]
    let hasExercisePlan: Bool
    let hasNutritionPlan: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("计划完成度")
                .font(.headline)

            PlanCompletionCard(
                title: "运动完成情况",
                items: exerciseItems,
                emptyText: hasExercisePlan ? "暂无目标" : "暂无处方"
            )

            PlanCompletionCard(
                title: "营养完成情况",
                items: nutritionItems,
                emptyText: hasNutritionPlan ? "暂无目标" : "暂无规划"
            )
        }
    }
}

private struct PlanCompletionCard: View {
    let title: String
    let items: [PlanProgressItem]
    let emptyText: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .foregroundColor(.secondary)
            if items.isEmpty {
                Text(emptyText)
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                ForEach(items) { item in
                    PlanProgressRow(item: item)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.04), radius: 2, y: 1)
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
