import Foundation
import Combine

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var lastSyncDate: Date?
    @Published var deviceId: String = ""
    @Published var userId: String = ""
    @Published var todaySteps: Int = 0
    @Published var latestHeartRate: Double?
    @Published var latestSpO2: Double?
    @Published var lastSleepHours: Double?
    @Published var todayIntakeKcal: Double?
    @Published var todayBurnedKcal: Double?
    @Published var todayWorkoutMinutes: Double?
    @Published var todayNutritionTotals: NutritionTotals?
    @Published var trend7d: [DashboardTrendPoint] = []
    @Published var trend30d: [DashboardTrendPoint] = []
    @Published var energyBalance: EnergyBalance?
    @Published var targets: HealthTargets?
    @Published var exercisePlan: ExercisePlanResponse?
    @Published var nutritionPlan: NutritionPlanResponse?
    @Published var dashboardError: String = ""

    private let healthKit = HealthKitManager()
    private let api = APIClient()
    private var isLiveUpdatesActive = false
    private var hasHealthKitAuthorization = false

    func load() {
        deviceId = DeviceIdentifier.current
        lastSyncDate = UserDefaults.standard.object(forKey: Constants.lastSyncDateKey) as? Date
        startLiveUpdates()
        Task { await refreshTodayData() }
    }

    func refreshTodayData() async {
        dashboardError = ""
        await refreshHealthMetrics()
        await refreshDietSummary()
        await refreshDashboardSummary()
        await refreshPlans()
    }

    func startLiveUpdates() {
        guard !isLiveUpdatesActive else { return }
        isLiveUpdatesActive = true
        Task { await configureLiveUpdates() }
    }

    func stopLiveUpdates() {
        isLiveUpdatesActive = false
        healthKit.stopLiveUpdates()
    }

    private func configureLiveUpdates() async {
        guard await ensureHealthKitAuthorized() else {
            isLiveUpdatesActive = false
            return
        }
        healthKit.startLiveUpdates(
            onSteps: { [weak self] in
                Task { await self?.refreshSteps() }
            },
            onHeartRate: { [weak self] in
                Task { await self?.refreshHeartRate() }
            },
            onSpO2: { [weak self] in
                Task { await self?.refreshSpO2() }
            },
            onSleep: { [weak self] in
                Task { await self?.refreshSleep() }
            },
            onWorkouts: { [weak self] in
                Task { await self?.refreshWorkouts() }
            }
        )
        await refreshHealthMetrics()
    }

    private func ensureHealthKitAuthorized() async -> Bool {
        guard healthKit.isAvailable else { return false }
        if hasHealthKitAuthorization { return true }
        do {
            try await healthKit.requestAuthorization()
            hasHealthKitAuthorization = true
            return true
        } catch {
            dashboardError = "HealthKit 授权失败"
            return false
        }
    }

    private func refreshHealthMetrics() async {
        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)

        guard await ensureHealthKitAuthorized() else { return }
        await refreshSteps(now: now, startOfDay: startOfDay)
        await refreshHeartRate(now: now, startOfDay: startOfDay)
        await refreshSpO2(now: now, startOfDay: startOfDay)
        await refreshSleep(startOfDay: startOfDay)
        await refreshWorkouts(now: now, startOfDay: startOfDay)
    }

    private func refreshDietSummary() async {
        let now = Date()
        do {
            let today = DateFormatters.dateOnly.string(from: now)
            let summary = try await api.fetchDietSummary(deviceId: deviceId, start: today, end: today)
            todayIntakeKcal = summary.totals.caloriesKcal
            todayNutritionTotals = summary.totals
        } catch {
            if todayIntakeKcal == nil {
                todayIntakeKcal = nil
            }
            todayNutritionTotals = nil
        }
    }

    private func refreshDashboardSummary() async {
        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)
        do {
            let today = DateFormatters.dateOnly.string(from: now)
            let start30 = DateFormatters.dateOnly.string(from: Calendar.current.date(byAdding: .day, value: -29, to: startOfDay) ?? startOfDay)
            let summary = try await api.fetchDashboardSummary(deviceId: deviceId, start: start30, end: today)
            applySummary(summary)
        } catch {
            dashboardError = "Dashboard 汇总数据获取失败"
        }
    }

    private func refreshPlans() async {
        let now = Date()
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
            exercisePlan = try await api.fetchExercisePlan(deviceId: planOwnerId, date: today)
        } catch {
            exercisePlan = nil
        }

        do {
            nutritionPlan = try await api.fetchNutritionPlan(deviceId: planOwnerId, date: today)
        } catch {
            nutritionPlan = nil
        }
    }

    private func refreshSteps(now: Date = Date(), startOfDay: Date? = nil) async {
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let steps = try? await healthKit.fetchDailySteps(start: start, end: now).first {
            todaySteps = steps.count
        }
    }

    private func refreshHeartRate(now: Date = Date(), startOfDay: Date? = nil) async {
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let hr = try? await healthKit.fetchHeartRateSamples(start: start, end: now).last {
            latestHeartRate = hr.bpm
        }
    }

    private func refreshSpO2(now: Date = Date(), startOfDay: Date? = nil) async {
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let spo2 = try? await healthKit.fetchSpO2Readings(start: start, end: now).last {
            latestSpO2 = spo2.percentage
        }
    }

    private func refreshSleep(startOfDay: Date? = nil) async {
        let todayStart = startOfDay ?? Calendar.current.startOfDay(for: Date())
        let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: todayStart)!
        if let sessions = try? await healthKit.fetchSleepSessions(start: yesterday, end: todayStart) {
            let totalSeconds = sessions.reduce(0.0) { acc, s in
                guard let start = ISO8601DateFormatter().date(from: s.startTime),
                      let end = ISO8601DateFormatter().date(from: s.endTime) else { return acc }
                return acc + end.timeIntervalSince(start)
            }
            if totalSeconds > 0 {
                lastSleepHours = totalSeconds / 3600.0
            }
        }
    }

    private func refreshWorkouts(now: Date = Date(), startOfDay: Date? = nil) async {
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let workouts = try? await healthKit.fetchWorkouts(start: start, end: now) {
            let totalSeconds = workouts.reduce(0.0) { acc, w in
                acc + w.durationSeconds
            }
            todayWorkoutMinutes = totalSeconds > 0 ? totalSeconds / 60.0 : nil
            let kcal = workouts.reduce(0.0) { acc, w in
                acc + (w.totalEnergyKcal ?? 0.0)
            }
            todayBurnedKcal = kcal > 0 ? kcal : nil
        }
    }

    private func applySummary(_ summary: DashboardSummaryResponse) {
        if let today = summary.today {
            if let steps = today.steps { todaySteps = steps }
            if let hr = today.latestHeartRate { latestHeartRate = hr }
            if let spo2 = today.latestSpO2 { latestSpO2 = spo2 }
            if let sleep = today.sleepHours { lastSleepHours = sleep }
            if let intake = today.intakeKcal { todayIntakeKcal = intake }
            if let burned = today.burnedKcal { todayBurnedKcal = burned }
        }
        trend7d = summary.trend7d ?? []
        trend30d = summary.trend30d ?? []
        energyBalance = summary.balance
        targets = summary.targets
    }
}
