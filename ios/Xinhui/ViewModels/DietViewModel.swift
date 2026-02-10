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
        let start = DateFormatters.dateOnly.string(from: startDate)
        let end = DateFormatters.dateOnly.string(from: now)

        do {
            async let summaryTask = api.fetchDietSummary(deviceId: deviceId, start: start, end: end)
            async let entriesTask = api.fetchDietEntries(deviceId: deviceId, start: start, end: end, limit: 200, offset: 0)
            let (summary, entries) = try await (summaryTask, entriesTask)

            last7Days = summary.days
            recentEntries = entries.entries

            let today = DateFormatters.dateOnly.string(from: now)
            todayTotals = summary.days.first(where: { $0.date == today })?.totals ?? .zero
        } catch let error as SyncError {
            currentError = error
        } catch {
            currentError = .networkError(underlying: error)
        }

        let today = DateFormatters.dateOnly.string(from: now)
        var planOwnerId = deviceId
        do {
            let me = try await api.fetchMe()
            userId = me.id
            planOwnerId = me.id
        } catch {
            userId = ""
        }

        do {
            nutritionPlan = try await api.fetchNutritionPlan(deviceId: planOwnerId, date: today)
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
            capturedAt: DateFormatters.iso8601.string(from: Date()),
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
        let payload = DietCreateEntryRequest(
            deviceId: DeviceIdentifier.current,
            eatenAt: DateFormatters.iso8601.string(from: eatenAt),
            mealType: mealType,
            items: items,
            notes: notes?.trimmingCharacters(in: .whitespacesAndNewlines),
            source: "vision",
            planId: planId
        )
        return try await api.createDietEntry(payload)
    }
}
