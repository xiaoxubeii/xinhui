import SwiftUI
import UIKit

private struct CapturedPhoto: Identifiable {
    let id = UUID()
    let image: UIImage
}

struct DietView: View {
    @StateObject private var viewModel = DietViewModel()
    @State private var showCamera = false
    @State private var capturedPhoto: CapturedPhoto?
    @State private var reviewPhoto: CapturedPhoto?

    var body: some View {
        let progressItems = PlanProgressBuilder.nutritionItems(
            plan: viewModel.nutritionPlan,
            totals: viewModel.todayTotals
        )

        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    NavigationLink(destination: NutritionPlanView(plan: viewModel.nutritionPlan)) {
                        PlanCard(
                            title: "营养规划",
                            subtitle: viewModel.nutritionPlan?.summary ?? "暂无规划，稍后再试",
                            iconName: "leaf.fill",
                            color: .green
                        )
                    }
                    .buttonStyle(.plain)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("今日完成情况")
                            .font(.headline)
                        if progressItems.isEmpty {
                            Text(viewModel.nutritionPlan == nil ? "暂无规划" : "暂无目标")
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

                    MetricCard(
                        title: "今日摄入",
                        value: String(format: "%.0f", viewModel.todayTotals.caloriesKcal),
                        unit: "kcal",
                        iconName: "fork.knife",
                        color: .orange
                    )

                    Button {
                        showCamera = true
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: "camera.fill")
                                .foregroundColor(.blue)
                            Text("拍照记录")
                                .font(.headline)
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

                    VStack(alignment: .leading, spacing: 12) {
                        HStack(spacing: 8) {
                            Text("最近记录")
                                .font(.headline)
                            Spacer()
                            if viewModel.isLoading && viewModel.recentEntries.isEmpty {
                                ProgressView()
                                    .scaleEffect(0.9)
                            }
                        }
                        if viewModel.isLoading && viewModel.recentEntries.isEmpty {
                            Text("正在加载…")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        } else if viewModel.recentEntries.isEmpty {
                            Text("暂无记录")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        } else {
                            ForEach(Array(viewModel.recentEntries.prefix(12).enumerated()), id: \.element.entryId) { idx, entry in
                                DietEntryRow(entry: entry)
                                if idx < min(viewModel.recentEntries.count, 12) - 1 {
                                    Divider()
                                }
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
                .padding(.horizontal)
                .padding(.vertical)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("营养")
            .onAppear { viewModel.load() }
            .refreshable { await viewModel.refresh() }
            .toolbar(.visible, for: .tabBar)
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
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showCamera = true
                    } label: {
                        Image(systemName: "camera")
                    }
                }
            }
            .fullScreenCover(isPresented: $showCamera) {
                DietCaptureView { image in
                    capturedPhoto = CapturedPhoto(image: image)
                    showCamera = false
                }
            }
            .sheet(item: $reviewPhoto) { photo in
                DietReviewView(image: photo.image, planId: viewModel.nutritionPlan?.planId) {
                    Task { await viewModel.refresh() }
                }
            }
            .onChange(of: capturedPhoto?.id) {
                guard let photo = capturedPhoto else { return }
                capturedPhoto = nil
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
                    reviewPhoto = photo
                }
            }
        }
    }
}

private struct DietEntryRow: View {
    let entry: DietEntry

    private var timeText: String {
        if let d = DateFormatters.iso8601Date(from: entry.eatenAt) {
            return DateFormatters.displayDateTime.string(from: d)
        }
        return entry.eatenAt
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(entry.mealType.displayName)
                    .font(.headline)
                Spacer()
                Text(String(format: "%.0f kcal", entry.totals.caloriesKcal))
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            Text(timeText)
                .font(.caption)
                .foregroundColor(.secondary)
            if let first = entry.items.first?.name, !first.isEmpty {
                Text(entry.items.prefix(3).map { $0.name }.joined(separator: "、"))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}
