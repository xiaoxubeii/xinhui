import SwiftUI
import UIKit

private struct EditableFoodItem: Identifiable {
    let id = UUID()
    var name: String
    var portion: String
    var grams: Double
    var caloriesKcal: Double
    var proteinG: Double
    var carbsG: Double
    var fatG: Double
    var confidence: Double?

    init(from item: DietFoodItem) {
        name = item.name
        portion = item.portion ?? ""
        grams = item.grams ?? 0
        caloriesKcal = item.caloriesKcal ?? 0
        proteinG = item.proteinG ?? 0
        carbsG = item.carbsG ?? 0
        fatG = item.fatG ?? 0
        confidence = item.confidence
    }

    init() {
        name = ""
        portion = ""
        grams = 0
        caloriesKcal = 0
        proteinG = 0
        carbsG = 0
        fatG = 0
        confidence = nil
    }

    func toAPIItem() -> DietFoodItem {
        DietFoodItem(
            name: name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "unknown" : name,
            portion: portion.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : portion,
            grams: grams > 0 ? grams : nil,
            caloriesKcal: caloriesKcal > 0 ? caloriesKcal : nil,
            proteinG: proteinG > 0 ? proteinG : nil,
            carbsG: carbsG > 0 ? carbsG : nil,
            fatG: fatG > 0 ? fatG : nil,
            confidence: confidence
        )
    }
}

private struct DietFoodCard: View {
    @Binding var item: EditableFoodItem
    let onDelete: () -> Void

    private let labelWidth: CGFloat = 72

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                TextField("食物名称", text: $item.name)
                    .font(.headline)

                Spacer()

                Button(role: .destructive) {
                    onDelete()
                } label: {
                    Image(systemName: "trash")
                }
                .buttonStyle(.plain)
            }

            Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 8) {
                GridRow {
                    label("重量")
                    numberField(value: $item.grams, unit: "g")
                }
                GridRow {
                    label("碳水")
                    numberField(value: $item.carbsG, unit: "g")
                }
                GridRow {
                    label("蛋白质")
                    numberField(value: $item.proteinG, unit: "g")
                }
                GridRow {
                    label("脂肪")
                    numberField(value: $item.fatG, unit: "g")
                }
                GridRow {
                    label("热量")
                    numberField(value: $item.caloriesKcal, unit: "kcal")
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(Constants.cornerRadius)
        .cardBorder()
        .shadow(color: .black.opacity(0.04), radius: 2, y: 1)
    }

    private func label(_ text: String) -> some View {
        Text(text)
            .foregroundColor(.secondary)
            .frame(width: labelWidth, alignment: .leading)
    }

    private func numberField(value: Binding<Double>, unit: String) -> some View {
        HStack(spacing: 6) {
            TextField("", value: value, format: .number)
                .keyboardType(.decimalPad)
                .multilineTextAlignment(.trailing)
                .frame(maxWidth: .infinity, alignment: .trailing)
            Text(unit)
                .foregroundColor(.secondary)
        }
    }
}

struct DietReviewView: View {
    let image: UIImage
    let planId: String?
    let onSaved: () -> Void

    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = DietViewModel()

    @State private var isRecognizing = true
    @State private var modelName: String = ""
    @State private var warnings: [String] = []
    @State private var editableItems: [EditableFoodItem] = []
    @State private var mealType: MealType = .snack
    @State private var eatenAt: Date = Date()
    @State private var notes: String = ""
    @State private var currentError: SyncError?
    @State private var isSaving = false

    private var computedTotals: NutritionTotals {
        var calories = 0.0
        var protein = 0.0
        var carbs = 0.0
        var fat = 0.0
        for item in editableItems {
            calories += item.caloriesKcal
            protein += item.proteinG
            carbs += item.carbsG
            fat += item.fatG
        }
        return NutritionTotals(
            caloriesKcal: (calories * 10).rounded() / 10,
            proteinG: (protein * 10).rounded() / 10,
            carbsG: (carbs * 10).rounded() / 10,
            fatG: (fat * 10).rounded() / 10
        )
    }

    var body: some View {
        NavigationView {
            Form {
                Section("照片") {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxWidth: .infinity)
                        .clipShape(RoundedRectangle(cornerRadius: Constants.cornerRadius))
                }

                Section("记录信息") {
                    DatePicker("进食时间", selection: $eatenAt)
                    Picker("餐次", selection: $mealType) {
                        ForEach(MealType.allCases) { type in
                            Text(type.displayName).tag(type)
                        }
                    }
                }

                Section("识别结果") {
                    if isRecognizing {
                        HStack {
                            ProgressView()
                            Text("正在识别…")
                                .foregroundColor(.secondary)
                        }
                    } else {
                        if editableItems.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("未识别到明确食物，请手动添加。")
                                    .foregroundColor(.secondary)
                            }
                        }

                        if !modelName.isEmpty {
                            Text("模型：\(modelName)")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        if !warnings.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                ForEach(warnings, id: \.self) { w in
                                    Text(w)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }

                        HStack {
                            Button {
                                Task { await recognize() }
                            } label: {
                                Label("重新识别", systemImage: "arrow.clockwise")
                            }
                            .disabled(isRecognizing)

                            Spacer()

                            Button {
                                editableItems.append(EditableFoodItem())
                            } label: {
                                Label("添加食物", systemImage: "plus")
                            }
                        }
                    }
                }

                if !editableItems.isEmpty {
                    Section("菜品") {
                        ForEach($editableItems) { $item in
                            DietFoodCard(item: $item) {
                                if let idx = editableItems.firstIndex(where: { $0.id == item.id }) {
                                    editableItems.remove(at: idx)
                                }
                            }
                            .listRowInsets(EdgeInsets(top: 6, leading: 0, bottom: 6, trailing: 0))
                            .listRowBackground(Color(.systemGroupedBackground))
                        }
                    }
                }

                Section("总计（估算）") {
                    LabeledContent("热量", value: String(format: "%.0f kcal", computedTotals.caloriesKcal))
                    LabeledContent("蛋白", value: String(format: "%.0f g", computedTotals.proteinG))
                    LabeledContent("碳水", value: String(format: "%.0f g", computedTotals.carbsG))
                    LabeledContent("脂肪", value: String(format: "%.0f g", computedTotals.fatG))
                }

                Section("备注") {
                    TextField("可选备注", text: $notes, axis: .vertical)
                        .lineLimit(3...6)
                }

                Section {
                    Text("说明：食物与热量为模型估算，请在保存前确认并适当修正。")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("确认饮食记录")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(isSaving ? "保存中…" : "保存") {
                        Task { await save() }
                    }
                    .disabled(isRecognizing || isSaving)
                }
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("取消") { dismiss() }
                }
            }
            .alert(
                "操作失败",
                isPresented: Binding(
                    get: { currentError != nil },
                    set: { if !$0 { currentError = nil } }
                ),
                presenting: currentError
            ) { _ in
                Button("确定", role: .cancel) {}
            } message: { error in
                Text(error.errorDescription ?? "未知错误")
            }
            .task { await recognize() }
        }
    }

    private func recognize() async {
        isRecognizing = true
        defer { isRecognizing = false }
        currentError = nil
        modelName = ""
        warnings = []
        editableItems = []

        do {
            let result = try await viewModel.recognize(image: image)
            modelName = result.model
            warnings = result.warnings
            editableItems = result.items.map { EditableFoodItem(from: $0) }
        } catch is CancellationError {
            return
        } catch let error as SyncError {
            currentError = error
        } catch {
            currentError = .networkError(underlying: error)
        }
    }

    private func save() async {
        isSaving = true
        defer { isSaving = false }

        do {
            _ = try await viewModel.saveEntry(
                eatenAt: eatenAt,
                mealType: mealType,
                items: editableItems.map { $0.toAPIItem() },
                notes: notes,
                planId: planId
            )
            onSaved()
            dismiss()
        } catch is CancellationError {
            return
        } catch let error as SyncError {
            currentError = error
        } catch {
            currentError = .networkError(underlying: error)
        }
    }
}
