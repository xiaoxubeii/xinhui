import Foundation

struct PlanProgressItem: Identifiable {
    let id = UUID()
    let title: String
    let current: Double
    let target: Double
    let unit: String

    var progress: Double {
        guard target > 0 else { return 0 }
        return min(current / target, 1.0)
    }
}

struct PlanProgressBuilder {
    static func exerciseItems(
        plan: ExercisePlanResponse?,
        todaySteps: Int,
        workoutMinutes: Double?,
        burnedKcal: Double?
    ) -> [PlanProgressItem] {
        guard let goals = plan?.goals else { return [] }
        var items: [PlanProgressItem] = []

        if let stepsTarget = goals.stepsTarget, stepsTarget > 0 {
            items.append(PlanProgressItem(
                title: "步数",
                current: Double(todaySteps),
                target: Double(stepsTarget),
                unit: "步"
            ))
        }
        if let minutesTarget = goals.minutesTarget, minutesTarget > 0 {
            items.append(PlanProgressItem(
                title: "时长",
                current: workoutMinutes ?? 0,
                target: minutesTarget,
                unit: "分钟"
            ))
        }
        if let kcalTarget = goals.kcalTarget, kcalTarget > 0 {
            items.append(PlanProgressItem(
                title: "消耗",
                current: burnedKcal ?? 0,
                target: kcalTarget,
                unit: "kcal"
            ))
        }

        return items
    }

    static func nutritionItems(
        plan: NutritionPlanResponse?,
        totals: NutritionTotals?
    ) -> [PlanProgressItem] {
        guard let macros = plan?.macros else { return [] }
        let current = totals ?? .zero
        var items: [PlanProgressItem] = []

        if let kcal = macros.kcal, kcal > 0 {
            items.append(PlanProgressItem(
                title: "热量",
                current: current.caloriesKcal,
                target: kcal,
                unit: "kcal"
            ))
        }
        if let protein = macros.proteinG, protein > 0 {
            items.append(PlanProgressItem(
                title: "蛋白质",
                current: current.proteinG,
                target: protein,
                unit: "g"
            ))
        }
        if let carbs = macros.carbsG, carbs > 0 {
            items.append(PlanProgressItem(
                title: "碳水",
                current: current.carbsG,
                target: carbs,
                unit: "g"
            ))
        }
        if let fat = macros.fatG, fat > 0 {
            items.append(PlanProgressItem(
                title: "脂肪",
                current: current.fatG,
                target: fat,
                unit: "g"
            ))
        }

        return items
    }
}
