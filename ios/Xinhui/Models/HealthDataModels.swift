import Foundation

/// 用户可选择同步的数据类型
enum HealthDataType: String, CaseIterable, Identifiable {
    case steps = "步数"
    case heartRate = "心率"
    case restingHeartRate = "静息心率"
    case spo2 = "血氧"
    case sleep = "睡眠"
    case workouts = "运动"

    var id: String { rawValue }

    var iconName: String {
        switch self {
        case .steps: return "figure.walk"
        case .heartRate: return "heart.fill"
        case .restingHeartRate: return "heart.text.square"
        case .spo2: return "lungs.fill"
        case .sleep: return "bed.double.fill"
        case .workouts: return "figure.run"
        }
    }
}

/// 同步进度
struct SyncProgress {
    var currentType: HealthDataType?
    var completedTypes: Set<HealthDataType> = []
    var phase: Phase = .idle

    enum Phase: String {
        case idle = "就绪"
        case querying = "正在读取数据"
        case uploading = "正在上传"
        case done = "完成"
        case failed = "失败"
    }

    var fractionCompleted: Double {
        let total = Double(HealthDataType.allCases.count + 1) // +1 for upload
        let done = Double(completedTypes.count) + (phase == .done ? 1.0 : 0.0)
        return min(done / total, 1.0)
    }
}

// MARK: - Dashboard Summary

struct DashboardSummaryResponse: Codable {
    let today: DashboardTodayMetrics?
    let trend7d: [DashboardTrendPoint]?
    let trend30d: [DashboardTrendPoint]?
    let balance: EnergyBalance?
    let targets: HealthTargets?

    enum CodingKeys: String, CodingKey {
        case today
        case trend7d = "trend_7d"
        case trend30d = "trend_30d"
        case balance
        case targets
    }
}

struct DashboardTodayMetrics: Codable {
    let steps: Int?
    let latestHeartRate: Double?
    let latestSpO2: Double?
    let sleepHours: Double?
    let intakeKcal: Double?
    let burnedKcal: Double?

    enum CodingKeys: String, CodingKey {
        case steps
        case latestHeartRate = "latest_heart_rate"
        case latestSpO2 = "latest_spo2"
        case sleepHours = "sleep_hours"
        case intakeKcal = "intake_kcal"
        case burnedKcal = "burned_kcal"
    }
}

struct DashboardTrendPoint: Codable, Identifiable {
    let date: String
    let steps: Int?
    let sleepHours: Double?
    let intakeKcal: Double?
    let burnedKcal: Double?

    var id: String { date }

    enum CodingKeys: String, CodingKey {
        case date
        case steps
        case sleepHours = "sleep_hours"
        case intakeKcal = "intake_kcal"
        case burnedKcal = "burned_kcal"
    }
}

struct EnergyBalance: Codable {
    let date: String?
    let deltaKcal: Double?
    let weeklyAvgKcal: Double?
    let targetDeltaKcal: Double?

    enum CodingKeys: String, CodingKey {
        case date
        case deltaKcal = "delta_kcal"
        case weeklyAvgKcal = "weekly_avg_kcal"
        case targetDeltaKcal = "target_delta_kcal"
    }
}

struct HealthTargets: Codable {
    let stepsTarget: Int?
    let sleepHoursTarget: Double?
    let intakeKcalTarget: Double?
    let burnedKcalTarget: Double?
    let energyDeltaTarget: Double?

    enum CodingKeys: String, CodingKey {
        case stepsTarget = "steps_target"
        case sleepHoursTarget = "sleep_hours_target"
        case intakeKcalTarget = "intake_kcal_target"
        case burnedKcalTarget = "burned_kcal_target"
        case energyDeltaTarget = "energy_delta_target"
    }
}

// MARK: - Lifestyle Summary (Dashboard)

struct LifestyleSummaryResponse: Codable {
    let deviceId: String
    let start: String
    let end: String
    let days: [LifestyleDay]

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case start
        case end
        case days
    }
}

struct LifestyleDay: Codable {
    let date: String
    let steps: Int?
    let workoutEnergyKcal: Double?
    let sleepHours: Double?
    let dietIntakeKcal: Double?
    let netKcal: Double?

    enum CodingKeys: String, CodingKey {
        case date
        case steps
        case workoutEnergyKcal = "workout_energy_kcal"
        case sleepHours = "sleep_hours"
        case dietIntakeKcal = "diet_intake_kcal"
        case netKcal = "net_kcal"
    }
}

// MARK: - Plans

struct ExercisePlanResponse: Codable {
    let planId: String?
    let title: String?
    let summary: String?
    let sessions: [ExerciseSession]
    let goals: ExerciseGoals?
    let generatedAt: String?
    let validFrom: String?
    let validTo: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case title
        case summary
        case sessions
        case goals
        case generatedAt = "generated_at"
        case validFrom = "valid_from"
        case validTo = "valid_to"
    }
}

struct ExerciseSession: Codable, Identifiable {
    let id: UUID = UUID()
    let type: String?
    let durationMin: Double?
    let intensity: String?
    let kcalEst: Double?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case type
        case durationMin = "duration_min"
        case intensity
        case kcalEst = "kcal_est"
        case notes
    }
}

struct ExerciseGoals: Codable {
    let stepsTarget: Int?
    let minutesTarget: Double?
    let kcalTarget: Double?
    let hrZone: String?

    enum CodingKeys: String, CodingKey {
        case stepsTarget = "steps_target"
        case minutesTarget = "minutes_target"
        case kcalTarget = "kcal_target"
        case hrZone = "hr_zone"
    }
}

struct NutritionPlanResponse: Codable {
    let planId: String?
    let title: String?
    let summary: String?
    let macros: NutritionMacros?
    let meals: [NutritionMeal]
    let constraints: NutritionConstraints?
    let generatedAt: String?
    let validFrom: String?
    let validTo: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case title
        case summary
        case macros
        case meals
        case constraints
        case generatedAt = "generated_at"
        case validFrom = "valid_from"
        case validTo = "valid_to"
    }
}

struct NutritionMacros: Codable {
    let kcal: Double?
    let proteinG: Double?
    let carbsG: Double?
    let fatG: Double?

    enum CodingKeys: String, CodingKey {
        case kcal
        case proteinG = "protein_g"
        case carbsG = "carbs_g"
        case fatG = "fat_g"
    }
}

struct NutritionMeal: Codable, Identifiable {
    let id: UUID = UUID()
    let mealType: String?
    let kcal: Double?
    let foods: [String]?

    enum CodingKeys: String, CodingKey {
        case mealType = "meal_type"
        case kcal
        case foods
    }
}

struct NutritionConstraints: Codable {
    let lowSugar: Bool?
    let lowSalt: Bool?
    let highFiber: Bool?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case lowSugar = "low_sugar"
        case lowSalt = "low_salt"
        case highFiber = "high_fiber"
        case notes
    }
}
