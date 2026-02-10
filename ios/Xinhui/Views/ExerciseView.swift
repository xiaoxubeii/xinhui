import SwiftUI

struct ExerciseView: View {
    @StateObject private var viewModel = ExerciseViewModel()

    var body: some View {
        let progressItems = PlanProgressBuilder.exerciseItems(
            plan: viewModel.exercisePlan,
            todaySteps: viewModel.todaySteps,
            workoutMinutes: viewModel.todayWorkoutMinutes,
            burnedKcal: viewModel.todayBurnedKcal
        )

        NavigationView {
            List {
                Section {
                    NavigationLink(destination: ExercisePlanView(plan: viewModel.exercisePlan)) {
                        PlanCard(
                            title: "运动处方",
                            subtitle: viewModel.exercisePlan?.summary ?? "暂无处方，稍后再试",
                            iconName: "figure.run",
                            color: .pink
                        )
                    }
                    .buttonStyle(.plain)
                }

                Section("今日完成情况") {
                    if progressItems.isEmpty {
                        Text(viewModel.exercisePlan == nil ? "暂无处方" : "暂无目标")
                            .foregroundColor(.secondary)
                    } else {
                        ForEach(progressItems) { item in
                            PlanProgressRow(item: item)
                        }
                    }
                }

                Section("今日概览") {
                    LabeledContent("步数", value: "\(viewModel.todaySteps) 步")
                    if let minutes = viewModel.todayWorkoutMinutes {
                        LabeledContent("运动时长", value: String(format: "%.0f 分钟", minutes))
                    } else {
                        LabeledContent("运动时长", value: "--")
                    }
                    if let kcal = viewModel.todayBurnedKcal {
                        LabeledContent("消耗", value: String(format: "%.0f kcal", kcal))
                    } else {
                        LabeledContent("消耗", value: "--")
                    }
                }
            }
            .listStyle(.insetGrouped)
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
