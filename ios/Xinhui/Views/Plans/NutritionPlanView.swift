import SwiftUI

struct NutritionPlanView: View {
    let plan: NutritionPlanResponse?

    var body: some View {
        List {
            Section(header: Text("摘要")) {
                Text(plan?.summary ?? "暂无规划")
            }

            if let macros = plan?.macros {
                Section(header: Text("营养目标")) {
                    if let kcal = macros.kcal { Text(String(format: "热量：%.0f kcal", kcal)) }
                    if let protein = macros.proteinG { Text(String(format: "蛋白质：%.0f g", protein)) }
                    if let carbs = macros.carbsG { Text(String(format: "碳水：%.0f g", carbs)) }
                    if let fat = macros.fatG { Text(String(format: "脂肪：%.0f g", fat)) }
                }
            }

            if let constraints = plan?.constraints {
                Section(header: Text("饮食约束")) {
                    if let lowSugar = constraints.lowSugar { Text("控糖：\(lowSugar ? "是" : "否")") }
                    if let lowSalt = constraints.lowSalt { Text("控盐：\(lowSalt ? "是" : "否")") }
                    if let highFiber = constraints.highFiber { Text("高纤维：\(highFiber ? "是" : "否")") }
                    if let notes = constraints.notes, !notes.isEmpty { Text(notes) }
                }
            }

            if let meals = plan?.meals, !meals.isEmpty {
                Section(header: Text("餐次建议")) {
                    ForEach(meals) { meal in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(meal.mealType ?? "餐次")
                                .font(.headline)
                            if let kcal = meal.kcal {
                                Text(String(format: "热量：%.0f kcal", kcal))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if let foods = meal.foods, !foods.isEmpty {
                                Text(foods.joined(separator: "、"))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
        }
        .navigationTitle(plan?.title ?? "营养规划")
        .toolbar(.hidden, for: .tabBar)
    }
}
