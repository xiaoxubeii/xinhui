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

struct DietReviewView: View {
    let image: UIImage
    let planId: String?
    let onSaved: () -> Void

    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = DietViewModel()

    @State private var isRecognizing = true
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
                    } else if editableItems.isEmpty {
                        Text("未识别到明确食物，请手动添加。")
                            .foregroundColor(.secondary)
                    }

                    ForEach($editableItems) { $item in
                        VStack(alignment: .leading, spacing: 8) {
                            TextField("食物名称", text: $item.name)
                            TextField("份量描述（可选）", text: $item.portion)

                            HStack {
                                TextField("克重", value: $item.grams, format: .number)
                                    .keyboardType(.decimalPad)
                                Text("g").foregroundColor(.secondary)
                                Spacer()
                                TextField("热量", value: $item.caloriesKcal, format: .number)
                                    .keyboardType(.decimalPad)
                                Text("kcal").foregroundColor(.secondary)
                            }

                            HStack {
                                TextField("蛋白", value: $item.proteinG, format: .number)
                                    .keyboardType(.decimalPad)
                                Text("g").foregroundColor(.secondary)
                                Spacer()
                                TextField("碳水", value: $item.carbsG, format: .number)
                                    .keyboardType(.decimalPad)
                                Text("g").foregroundColor(.secondary)
                                Spacer()
                                TextField("脂肪", value: $item.fatG, format: .number)
                                    .keyboardType(.decimalPad)
                                Text("g").foregroundColor(.secondary)
                            }

                            Button(role: .destructive) {
                                if let idx = editableItems.firstIndex(where: { $0.id == item.id }) {
                                    editableItems.remove(at: idx)
                                }
                            } label: {
                                Label("删除此食物", systemImage: "trash")
                            }
                        }
                    }

                    Button {
                        editableItems.append(EditableFoodItem())
                    } label: {
                        Label("添加食物", systemImage: "plus")
                    }
                }

                Section("总计（估算）") {
                    LabeledContent("热量", value: String(format: "%.0f kcal", computedTotals.caloriesKcal))
                    LabeledContent("蛋白", value: String(format: "%.0f g", computedTotals.proteinG))
                    LabeledContent("碳水", value: String(format: "%.0f g", computedTotals.carbsG))
                    LabeledContent("脂肪", value: String(format: "%.0f g", computedTotals.fatG))
                }

                if !warnings.isEmpty {
                    Section("提示") {
                        ForEach(warnings, id: \.self) { w in
                            Text(w).foregroundColor(.secondary)
                        }
                    }
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
        currentError = nil
        warnings = []
        editableItems = []

        do {
            let result = try await viewModel.recognize(image: image)
            warnings = result.warnings
            editableItems = result.items.map { EditableFoodItem(from: $0) }
        } catch let error as SyncError {
            currentError = error
        } catch {
            currentError = .networkError(underlying: error)
        }

        isRecognizing = false
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
        } catch let error as SyncError {
            currentError = error
        } catch {
            currentError = .networkError(underlying: error)
        }
    }
}
