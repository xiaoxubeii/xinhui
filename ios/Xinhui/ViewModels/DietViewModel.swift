import Foundation
import Combine
import UIKit

@MainActor
final class DietViewModel: ObservableObject {
    @Published var deviceId: String = ""
    @Published var userId: String = ""
    @Published var todayTotals: NutritionTotals = .zero
    @Published var recentEntries: [DietEntry] = []
    @Published var last7Days: [DietDailySummary] = []
    @Published var nutritionPlan: NutritionPlanResponse?
    @Published var isLoading = false
    @Published var currentError: SyncError?

    private let api: APIClient

    init(apiClient: APIClient = APIClient()) {
        self.api = apiClient
    }

    func load() {
        deviceId = DeviceIdentifier.current
        Task { await refresh() }
    }

    func refresh() async {
        guard !deviceId.isEmpty else { return }
        isLoading = true
        currentError = nil
        defer { isLoading = false }

        let now = Date()
        let startDate = Calendar.current.date(byAdding: .day, value: -6, to: Calendar.current.startOfDay(for: now))!
        let start = DateFormatters.dateOnlyString(from: startDate)
        let end = DateFormatters.dateOnlyString(from: now)

        do {
            async let summaryTask = api.fetchDietSummary(deviceId: deviceId, start: start, end: end)
            async let entriesTask = api.fetchDietEntries(deviceId: deviceId, start: start, end: end, limit: 200, offset: 0)
            let (summary, entries) = try await (summaryTask, entriesTask)

            last7Days = summary.days
            recentEntries = entries.entries.sorted { lhs, rhs in
                let leftDate = DateFormatters.iso8601Date(from: lhs.eatenAt)
                let rightDate = DateFormatters.iso8601Date(from: rhs.eatenAt)
                switch (leftDate, rightDate) {
                case let (l?, r?):
                    if l != r { return l > r }
                case (nil, nil):
                    break
                case (_?, nil):
                    return true
                case (nil, _?):
                    return false
                }
                return lhs.eatenAt > rhs.eatenAt
            }

            let today = DateFormatters.dateOnlyString(from: now)
            todayTotals = summary.days.first(where: { $0.date == today })?.totals ?? .zero
        } catch is CancellationError {
            return
        } catch let error as SyncError {
            currentError = error
        } catch {
            currentError = .networkError(underlying: error)
        }

        let today = DateFormatters.dateOnlyString(from: now)
        var planOwnerId = deviceId
        do {
            let me = try await api.fetchMe()
            userId = me.id
            planOwnerId = me.id
        } catch is CancellationError {
            return
        } catch {
            userId = ""
        }

        do {
            nutritionPlan = try await api.fetchNutritionPlan(deviceId: planOwnerId, date: today)
        } catch is CancellationError {
            return
        } catch {
            nutritionPlan = nil
        }
    }

    func recognize(image: UIImage) async throws -> DietRecognizeResponse {
        let deviceId = DeviceIdentifier.current
        guard let base64 = ImageEncoding.jpegBase64(from: image) else {
            throw SyncError.encodingFailed
        }

        let payload = DietRecognizeRequest(
            deviceId: deviceId,
            capturedAt: DateFormatters.iso8601String(from: Date()),
            imageMime: "image/jpeg",
            imageBase64: base64,
            locale: "zh-CN"
        )
        return try await api.recognizeFood(payload)
    }

    func saveEntry(
        eatenAt: Date,
        mealType: MealType,
        items: [DietFoodItem],
        notes: String?,
        planId: String?
    ) async throws -> DietCreateEntryResponse {
        let eatenAtISO = DateFormatters.iso8601String(from: eatenAt)
        let payload = DietCreateEntryRequest(
            deviceId: DeviceIdentifier.current,
            eatenAt: eatenAtISO,
            mealType: mealType,
            items: items,
            notes: notes?.trimmingCharacters(in: .whitespacesAndNewlines),
            source: "vision",
            planId: planId
        )
        let response = try await api.createDietEntry(payload)
        let totalsInfo: [String: Double] = [
            "calories_kcal": response.totals.caloriesKcal,
            "protein_g": response.totals.proteinG,
            "carbs_g": response.totals.carbsG,
            "fat_g": response.totals.fatG,
        ]
        NotificationCenter.default.post(
            name: .dietEntrySaved,
            object: nil,
            userInfo: [
                DietNotificationKeys.totals: totalsInfo,
                DietNotificationKeys.eatenAt: eatenAtISO,
            ]
        )
        return response
    }
}
