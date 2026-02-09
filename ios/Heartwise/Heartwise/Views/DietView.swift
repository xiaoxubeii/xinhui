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
        NavigationView {
            List {
                Section {
                    HStack(spacing: 12) {
                        MetricCard(
                            title: "今日摄入",
                            value: String(format: "%.0f", viewModel.todayTotals.caloriesKcal),
                            unit: "kcal",
                            iconName: "fork.knife",
                            color: .orange
                        )
                    }
                    .listRowInsets(EdgeInsets())
                    .padding(.vertical, 8)
                }

                Section {
                    Button {
                        showCamera = true
                    } label: {
                        HStack {
                            Spacer()
                            Image(systemName: "camera.fill")
                            Text("拍照记录")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                }

                Section("最近记录") {
                    if viewModel.isLoading && viewModel.recentEntries.isEmpty {
                        HStack {
                            ProgressView()
                            Text("正在加载…").foregroundColor(.secondary)
                        }
                    } else if viewModel.recentEntries.isEmpty {
                        Text("暂无记录")
                            .foregroundColor(.secondary)
                    } else {
                        ForEach(viewModel.recentEntries, id: \.entryId) { entry in
                            DietEntryRow(entry: entry)
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
            .navigationTitle("饮食管理")
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
                DietReviewView(image: photo.image) {
                    Task { await viewModel.refresh() }
                }
            }
            .onChange(of: capturedPhoto?.id) { _ in
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
        if let d = DateFormatters.iso8601.date(from: entry.eatenAt) {
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
