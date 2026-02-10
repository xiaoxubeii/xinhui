import Foundation

// MARK: - Nutrition

struct NutritionTotals: Codable {
    var caloriesKcal: Double
    var proteinG: Double
    var carbsG: Double
    var fatG: Double

    enum CodingKeys: String, CodingKey {
        case caloriesKcal = "calories_kcal"
        case proteinG = "protein_g"
        case carbsG = "carbs_g"
        case fatG = "fat_g"
    }

    static let zero = NutritionTotals(caloriesKcal: 0, proteinG: 0, carbsG: 0, fatG: 0)
}

struct DietFoodItem: Codable {
    var name: String
    var portion: String?
    var grams: Double?
    var caloriesKcal: Double?
    var proteinG: Double?
    var carbsG: Double?
    var fatG: Double?
    var confidence: Double?

    enum CodingKeys: String, CodingKey {
        case name
        case portion
        case grams
        case caloriesKcal = "calories_kcal"
        case proteinG = "protein_g"
        case carbsG = "carbs_g"
        case fatG = "fat_g"
        case confidence
    }
}

// MARK: - Recognize

struct DietRecognizeRequest: Codable {
    let deviceId: String
    let capturedAt: String
    let imageMime: String
    let imageBase64: String
    let locale: String?

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case capturedAt = "captured_at"
        case imageMime = "image_mime"
        case imageBase64 = "image_base64"
        case locale
    }
}

struct DietRecognizeResponse: Codable {
    let requestId: String
    let items: [DietFoodItem]
    let totals: NutritionTotals
    let warnings: [String]
    let model: String

    enum CodingKeys: String, CodingKey {
        case requestId = "request_id"
        case items
        case totals
        case warnings
        case model
    }
}

// MARK: - Entries

enum MealType: String, CaseIterable, Identifiable, Codable {
    case breakfast
    case lunch
    case dinner
    case snack

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .breakfast: return "早餐"
        case .lunch: return "午餐"
        case .dinner: return "晚餐"
        case .snack: return "加餐"
        }
    }
}

struct DietCreateEntryRequest: Codable {
    let deviceId: String
    let eatenAt: String
    let mealType: MealType
    let items: [DietFoodItem]
    let notes: String?
    let source: String?
    let planId: String?

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case eatenAt = "eaten_at"
        case mealType = "meal_type"
        case items
        case notes
        case source
        case planId = "plan_id"
    }
}

struct DietCreateEntryResponse: Codable {
    let entryId: String
    let savedAt: String
    let totals: NutritionTotals

    enum CodingKeys: String, CodingKey {
        case entryId = "entry_id"
        case savedAt = "saved_at"
        case totals
    }
}

struct DietEntry: Codable {
    let entryId: String
    let deviceId: String
    let createdAt: String
    let eatenAt: String
    let mealType: MealType
    let items: [DietFoodItem]
    let totals: NutritionTotals
    let notes: String?
    let source: String
    let warnings: [String]
    let planId: String?

    enum CodingKeys: String, CodingKey {
        case entryId = "entry_id"
        case deviceId = "device_id"
        case createdAt = "created_at"
        case eatenAt = "eaten_at"
        case mealType = "meal_type"
        case items
        case totals
        case notes
        case source
        case warnings
        case planId = "plan_id"
    }
}

struct DietEntriesResponse: Codable {
    let deviceId: String
    let count: Int
    let entries: [DietEntry]

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case count
        case entries
    }
}

struct DietDailySummary: Codable, Identifiable {
    var id: String { date }
    let date: String
    let totals: NutritionTotals
    let entryCount: Int

    enum CodingKeys: String, CodingKey {
        case date
        case totals
        case entryCount = "entry_count"
    }
}

struct DietSummaryResponse: Codable {
    let deviceId: String
    let start: String
    let end: String
    let totals: NutritionTotals
    let days: [DietDailySummary]

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case start
        case end
        case totals
        case days
    }
}
