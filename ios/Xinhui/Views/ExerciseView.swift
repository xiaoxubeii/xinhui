import SwiftUI
import Charts

struct ExerciseView: View {
    @StateObject private var viewModel = ExerciseViewModel()
    @State private var breakdownMetric: BreakdownMetric = .minutes

    var body: some View {
        let progressItems = PlanProgressBuilder.exerciseItems(
            plan: viewModel.exercisePlan,
            todaySteps: viewModel.todaySteps,
            workoutMinutes: viewModel.todayWorkoutMinutes,
            burnedKcal: viewModel.todayBurnedKcal
        )

        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    NavigationLink(destination: ExercisePlanView(plan: viewModel.exercisePlan)) {
                        PlanCard(
                            title: "运动规划",
                            subtitle: viewModel.exercisePlan?.summary ?? "暂无规划，稍后再试",
                            iconName: "figure.run",
                            color: .pink
                        )
                    }
                    .buttonStyle(.plain)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("今日完成情况")
                            .font(.headline)
                        if progressItems.isEmpty {
                            Text(viewModel.exercisePlan == nil ? "暂无规划" : "暂无目标")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        } else {
                            ForEach(progressItems) { item in
                                PlanProgressRow(item: item)
                            }
                        }
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.systemBackground))
                    .cornerRadius(Constants.cornerRadius)
                    .cardBorder()
                    .shadow(color: .black.opacity(0.04), radius: 2, y: 1)

                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                    ], spacing: 12) {
                        MetricCard(
                            title: "步数",
                            value: "\(viewModel.todaySteps)",
                            unit: "步",
                            iconName: "figure.walk",
                            color: .green
                        )

                        MetricCard(
                            title: "运动时长",
                            value: viewModel.todayWorkoutMinutes.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "分钟",
                            iconName: "timer",
                            color: .blue
                        )

                        MetricCard(
                            title: "消耗",
                            value: viewModel.todayBurnedKcal.map { String(format: "%.0f", $0) } ?? "--",
                            unit: "kcal",
                            iconName: "flame.fill",
                            color: .orange
                        )
                    }

                    WorkoutBreakdownCard(
                        metric: $breakdownMetric,
                        stats: viewModel.workoutStats
                    )
                }
                .padding(.horizontal)
                .padding(.vertical)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("运动")
            .onAppear { viewModel.load() }
            .refreshable { await viewModel.refresh() }
            .alert(
                "加载失败",
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
}

private enum BreakdownMetric: String, CaseIterable, Identifiable {
    case minutes = "时长"
    case kcal = "热量"

    var id: String { rawValue }

    var unit: String {
        switch self {
        case .minutes: return "分钟"
        case .kcal: return "kcal"
        }
    }
}

private struct WorkoutBreakdownCard: View {
    @Binding var metric: BreakdownMetric
    let stats: [WorkoutCategoryStat]

    private var visibleStats: ArraySlice<WorkoutCategoryStat> {
        stats.prefix(8)
    }

    private var maxValue: Double {
        visibleStats.map { stat in
            switch metric {
            case .minutes: return stat.minutes
            case .kcal: return stat.kcal
            }
        }
        .max() ?? 0
    }

    private func valueText(for stat: WorkoutCategoryStat) -> String {
        switch metric {
        case .minutes:
            return String(format: "%.0f %@", stat.minutes, metric.unit)
        case .kcal:
            return String(format: "%.0f %@", stat.kcal, metric.unit)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("按类型统计")
                    .font(.headline)
                Spacer()
                Picker("指标", selection: $metric) {
                    ForEach(BreakdownMetric.allCases) { m in
                        Text(m.rawValue).tag(m)
                    }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 160)
            }

            if visibleStats.isEmpty {
                Text("今天暂无运动记录")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                Chart {
                    ForEach(visibleStats) { stat in
                        let value = metric == .minutes ? stat.minutes : stat.kcal
                        BarMark(
                            x: .value(metric.rawValue, value),
                            y: .value("类型", stat.displayName)
                        )
                        .foregroundStyle(.blue.opacity(0.8))
                        .annotation(position: .trailing) {
                            Text(valueText(for: stat))
                                .font(.caption2)
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .frame(height: max(160, CGFloat(visibleStats.count) * 22 + 40))
                .chartXScale(domain: 0...max(1.0, maxValue * 1.1))
                .chartXAxis {
                    AxisMarks(position: .bottom, values: .automatic(desiredCount: 4))
                }
                .chartYAxis {
                    AxisMarks(position: .leading)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .cardBorder()
        .shadow(color: .black.opacity(0.04), radius: 2, y: 1)
    }
}
