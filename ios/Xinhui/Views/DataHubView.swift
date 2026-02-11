import SwiftUI
import Charts

struct DataHubView: View {
    @ObservedObject var viewModel: DashboardViewModel
    @State private var selectedRange: TrendRange = .days7
    @State private var selectedMetric: TrendMetric = .steps

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    ActivityRingsCard(viewModel: viewModel)

                    TrendChartCard(
                        selectedRange: $selectedRange,
                        selectedMetric: $selectedMetric,
                        trend7d: viewModel.trend7d,
                        trend30d: viewModel.trend30d
                    )

                    NavigationLink(destination: HealthDataView()) {
                        HStack(spacing: 12) {
                            Image(systemName: "list.bullet.rectangle")
                                .font(.title3)
                                .foregroundColor(.blue)
                            VStack(alignment: .leading, spacing: 4) {
                                Text("数据浏览")
                                    .font(.headline)
                                Text("查看近 7 天原始数据")
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
                        .cornerRadius(Constants.cornerRadius)
                        .cardBorder()
                        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal)
                .padding(.vertical)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("数据")
            .refreshable { await viewModel.refreshTodayData() }
        }
    }
}

private enum TrendRange: String, CaseIterable, Identifiable {
    case days7 = "近7天"
    case days30 = "近30天"

    var id: String { rawValue }
}

private enum TrendMetric: String, CaseIterable, Identifiable {
    case steps = "步数"
    case sleep = "睡眠"
    case intake = "摄入"
    case burned = "消耗"

    var id: String { rawValue }

    var unit: String {
        switch self {
        case .steps: return "步"
        case .sleep: return "小时"
        case .intake, .burned: return "kcal"
        }
    }

    var color: Color {
        switch self {
        case .steps: return .green
        case .sleep: return .purple
        case .intake: return .orange
        case .burned: return .pink
        }
    }

    func value(from point: DashboardTrendPoint) -> Double? {
        switch self {
        case .steps:
            return point.steps.map(Double.init)
        case .sleep:
            return point.sleepHours
        case .intake:
            return point.intakeKcal
        case .burned:
            return point.burnedKcal
        }
    }
}

private struct ActivityRingsCard: View {
    @ObservedObject var viewModel: DashboardViewModel

    private var stepsTarget: Double {
        let planTarget = Double(viewModel.exercisePlan?.goals?.stepsTarget ?? 0)
        return planTarget > 0 ? planTarget : 10_000
    }

    private var minutesTarget: Double {
        let planTarget = viewModel.exercisePlan?.goals?.minutesTarget ?? 0
        return planTarget > 0 ? planTarget : 30
    }

    private var burnedTarget: Double {
        let planTarget = viewModel.exercisePlan?.goals?.kcalTarget ?? 0
        return planTarget > 0 ? planTarget : 500
    }

    private func progress(current: Double, target: Double) -> Double {
        guard target > 0 else { return 0 }
        return min(current / target, 1.0)
    }

    var body: some View {
        let steps = Double(viewModel.todaySteps)
        let minutes = viewModel.todayWorkoutMinutes ?? 0
        let burned = viewModel.todayBurnedKcal ?? 0

        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("今日概览")
                    .font(.headline)
                Spacer()
                if let lastSync = viewModel.lastSyncDate {
                    Text(DateFormatters.displayDateTime.string(from: lastSync))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            HStack(alignment: .center, spacing: 16) {
                ActivityRingsView(
                    rings: [
                        RingSpec(progress: progress(current: burned, target: burnedTarget), color: .pink, lineWidth: 14),
                        RingSpec(progress: progress(current: minutes, target: minutesTarget), color: .blue, lineWidth: 14),
                        RingSpec(progress: progress(current: steps, target: stepsTarget), color: .green, lineWidth: 14),
                    ]
                )
                .frame(width: 120, height: 120)

                VStack(alignment: .leading, spacing: 10) {
                    RingMetricRow(
                        title: "消耗",
                        valueText: burned > 0 ? String(format: "%.0f", burned) : "--",
                        targetText: String(format: "%.0f", burnedTarget),
                        unit: "kcal",
                        color: .pink,
                        iconName: "flame.fill"
                    )
                    RingMetricRow(
                        title: "运动",
                        valueText: minutes > 0 ? String(format: "%.0f", minutes) : "--",
                        targetText: String(format: "%.0f", minutesTarget),
                        unit: "分钟",
                        color: .blue,
                        iconName: "timer"
                    )
                    RingMetricRow(
                        title: "步数",
                        valueText: steps > 0 ? String(format: "%.0f", steps) : "--",
                        targetText: String(format: "%.0f", stepsTarget),
                        unit: "步",
                        color: .green,
                        iconName: "figure.walk"
                    )
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .cardBorder()
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}

private struct RingMetricRow: View {
    let title: String
    let valueText: String
    let targetText: String
    let unit: String
    let color: Color
    let iconName: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: iconName)
                .foregroundColor(color)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text("\(valueText) / \(targetText) \(unit)")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
        }
    }
}

private struct TrendChartCard: View {
    @Binding var selectedRange: TrendRange
    @Binding var selectedMetric: TrendMetric
    let trend7d: [DashboardTrendPoint]
    let trend30d: [DashboardTrendPoint]

    private var data: [DashboardTrendPoint] {
        switch selectedRange {
        case .days7: return trend7d
        case .days30: return trend30d
        }
    }

    private var maxValue: Double {
        data.compactMap { selectedMetric.value(from: $0) }.max() ?? 0
    }

    private var averageValue: Double? {
        let values = data.compactMap { selectedMetric.value(from: $0) }
        guard !values.isEmpty else { return nil }
        return values.reduce(0, +) / Double(values.count)
    }

    private func date(for point: DashboardTrendPoint) -> Date? {
        DateFormatters.dateOnlyDate(from: point.date)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("趋势")
                    .font(.headline)
                Spacer()
                Picker("范围", selection: $selectedRange) {
                    ForEach(TrendRange.allCases) { range in
                        Text(range.rawValue).tag(range)
                    }
                }
                .pickerStyle(.segmented)
            }

            Picker("指标", selection: $selectedMetric) {
                ForEach(TrendMetric.allCases) { metric in
                    Text(metric.rawValue).tag(metric)
                }
            }
            .pickerStyle(.segmented)

            if data.isEmpty {
                Text("暂无趋势数据")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                Chart {
                    ForEach(data) { point in
                        if let date = date(for: point),
                           let value = selectedMetric.value(from: point) {
                            AreaMark(
                                x: .value("日期", date),
                                y: .value(selectedMetric.rawValue, value)
                            )
                            .foregroundStyle(selectedMetric.color.opacity(0.18))

                            LineMark(
                                x: .value("日期", date),
                                y: .value(selectedMetric.rawValue, value)
                            )
                            .interpolationMethod(.catmullRom)
                            .foregroundStyle(selectedMetric.color)
                        }
                    }
                }
                .frame(height: 180)
                .chartYScale(domain: 0...max(1.0, maxValue * 1.1))
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 4)) { value in
                        if let date = value.as(Date.self) {
                            AxisValueLabel(DateFormatters.displayDate.string(from: date))
                        }
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading, values: .automatic(desiredCount: 3))
                }

                if let avg = averageValue {
                    Text("均值 \(String(format: selectedMetric == .steps ? "%.0f" : "%.1f", avg)) \(selectedMetric.unit)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .cardBorder()
        .shadow(color: .black.opacity(0.05), radius: 4, y: 2)
    }
}

private struct RingSpec: Identifiable {
    let id = UUID()
    let progress: Double
    let color: Color
    let lineWidth: CGFloat
}

private struct ActivityRingsView: View {
    let rings: [RingSpec]

    var body: some View {
        ZStack {
            ForEach(Array(rings.enumerated()), id: \.element.id) { idx, ring in
                let inset = CGFloat(idx) * (ring.lineWidth + 6)
                Circle()
                    .stroke(ring.color.opacity(0.15), style: StrokeStyle(lineWidth: ring.lineWidth, lineCap: .round))
                    .padding(inset)
                Circle()
                    .trim(from: 0, to: min(max(ring.progress, 0), 1.0))
                    .stroke(ring.color, style: StrokeStyle(lineWidth: ring.lineWidth, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                    .padding(inset)
            }
        }
    }
}
