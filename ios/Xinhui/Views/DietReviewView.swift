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

private struct DietItemsTable: View {
    let items: [EditableFoodItem]

    private let columns: [GridItem] = [
        GridItem(.fixed(140), alignment: .leading),
        GridItem(.fixed(90), alignment: .trailing),
        GridItem(.fixed(100), alignment: .trailing),
        GridItem(.fixed(90), alignment: .trailing),
        GridItem(.fixed(90), alignment: .trailing),
        GridItem(.fixed(90), alignment: .trailing),
    ]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            LazyVGrid(columns: columns, alignment: .leading, spacing: 8) {
                headerCell("菜品")
                headerCell("重量(g)")
                headerCell("卡路里(kcal)")
                headerCell("蛋白质(g)")
                headerCell("碳水(g)")
                headerCell("脂肪(g)")

                ForEach(items) { item in
                    Text(displayName(for: item))
                        .lineLimit(1)

                    Text(weightText(for: item))
                        .lineLimit(1)

                    Text(formatNumber(item.caloriesKcal))
                        .lineLimit(1)

                    Text(formatNumber(item.proteinG))
                        .lineLimit(1)

                    Text(formatNumber(item.carbsG))
                        .lineLimit(1)

                    Text(formatNumber(item.fatG))
                        .lineLimit(1)
                }
            }
            .font(.caption)
            .padding(.vertical, 4)
        }
    }

    private func headerCell(_ title: String) -> some View {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundColor(.secondary)
    }

    private func displayName(for item: EditableFoodItem) -> String {
        let trimmed = item.name.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? "食物" : trimmed
    }

    private func weightText(for item: EditableFoodItem) -> String {
        if item.grams > 0 {
            return formatNumber(item.grams)
        }
        let portion = item.portion.trimmingCharacters(in: .whitespacesAndNewlines)
        return portion.isEmpty ? "—" : portion
    }

    private func formatNumber(_ value: Double) -> String {
        guard value > 0 else { return "—" }
        let rounded = value.rounded()
        if abs(rounded - value) < 0.05 {
            return String(format: "%.0f", value)
        }
        return String(format: "%.1f", value)
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
                    Section("识别明细") {
                        DietItemsTable(items: editableItems)
                    }
                }

                ForEach($editableItems) { $item in
                    Section(item.name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "食物" : item.name) {
                        TextField("食物名称", text: $item.name)
                        TextField("份量描述（可选）", text: $item.portion)
                        TextField("克重 (g)", value: $item.grams, format: .number)
                            .keyboardType(.decimalPad)
                        TextField("热量 (kcal)", value: $item.caloriesKcal, format: .number)
                            .keyboardType(.decimalPad)
                        TextField("蛋白 (g)", value: $item.proteinG, format: .number)
                            .keyboardType(.decimalPad)
                        TextField("碳水 (g)", value: $item.carbsG, format: .number)
                            .keyboardType(.decimalPad)
                        TextField("脂肪 (g)", value: $item.fatG, format: .number)
                            .keyboardType(.decimalPad)
                        if let confidence = item.confidence {
                            LabeledContent("置信度", value: String(format: "%.0f%%", confidence * 100.0))
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
