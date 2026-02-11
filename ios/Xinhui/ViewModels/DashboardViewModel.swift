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
    private let defaults = UserDefaults.standard
    private var currentDayKey: String = ""
    private var didRestoreCache = false
    private var dietEntryObserver: NSObjectProtocol?

    func load() {
        deviceId = DeviceIdentifier.current
        lastSyncDate = defaults.object(forKey: Constants.lastSyncDateKey) as? Date
        ensureDailyState()
        if !didRestoreCache {
            restoreCachedMetrics()
            didRestoreCache = true
        }
        registerDietEntryObserver()
        startLiveUpdates()
        Task { await refreshTodayData() }
    }

    deinit {
        if let observer = dietEntryObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }

    private func registerDietEntryObserver() {
        guard dietEntryObserver == nil else { return }
        dietEntryObserver = NotificationCenter.default.addObserver(
            forName: .dietEntrySaved,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task {
                await self?.refreshDietSummary()
                self?.persistCachedMetrics()
            }
        }
    }

    func refreshTodayData() async {
        ensureDailyState()
        dashboardError = ""
        await refreshHealthMetrics()
        await refreshDietSummary()
        await refreshDashboardSummary()
        await refreshPlans()
        persistCachedMetrics()
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
        ensureDailyState()
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
        ensureDailyState()
        let now = Date()
        do {
            let today = DateFormatters.dateOnlyString(from: now)
            let summary = try await api.fetchDietSummary(deviceId: deviceId, start: today, end: today)
            todayIntakeKcal = summary.totals.caloriesKcal
            todayNutritionTotals = summary.totals
        } catch {
            // Keep last known values if request fails.
        }
    }

    private func refreshDashboardSummary() async {
        ensureDailyState()
        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)
        do {
            let today = DateFormatters.dateOnlyString(from: now)
            let start30 = DateFormatters.dateOnlyString(from: Calendar.current.date(byAdding: .day, value: -29, to: startOfDay) ?? startOfDay)
            let summary = try await api.fetchLifestyleSummary(deviceId: deviceId, start: start30, end: today)
            applyLifestyleSummary(summary, today: today)
        } catch is CancellationError {
            return
        } catch {
            if let syncError = error as? SyncError {
                dashboardError = syncError.errorDescription ?? "Dashboard 汇总数据获取失败"
            } else if let localized = (error as? LocalizedError)?.errorDescription {
                dashboardError = localized
            } else {
                dashboardError = "Dashboard 汇总数据获取失败: \(error.localizedDescription)"
            }
        }
    }

    private func refreshPlans() async {
        let now = Date()
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
            exercisePlan = try await api.fetchExercisePlan(deviceId: planOwnerId, date: today)
        } catch is CancellationError {
            return
        } catch {
            exercisePlan = nil
        }

        do {
            nutritionPlan = try await api.fetchNutritionPlan(deviceId: planOwnerId, date: today)
        } catch is CancellationError {
            return
        } catch {
            nutritionPlan = nil
        }
    }

    private func refreshSteps(now: Date = Date(), startOfDay: Date? = nil) async {
        ensureDailyState(now: now)
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let steps = try? await healthKit.fetchDailySteps(start: start, end: now).first {
            let value = steps.count
            if value >= todaySteps {
                todaySteps = value
                defaults.set(value, forKey: Constants.dashboardCacheStepsKey)
            }
        }
    }

    private func refreshHeartRate(now: Date = Date(), startOfDay: Date? = nil) async {
        ensureDailyState(now: now)
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let hr = try? await healthKit.fetchHeartRateSamples(start: start, end: now).last {
            latestHeartRate = hr.bpm
        }
    }

    private func refreshSpO2(now: Date = Date(), startOfDay: Date? = nil) async {
        ensureDailyState(now: now)
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let spo2 = try? await healthKit.fetchSpO2Readings(start: start, end: now).last {
            latestSpO2 = spo2.percentage
        }
    }

    private func refreshSleep(startOfDay: Date? = nil) async {
        let todayStart = startOfDay ?? Calendar.current.startOfDay(for: Date())
        ensureDailyState(now: todayStart)
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
        ensureDailyState(now: now)
        let start = startOfDay ?? Calendar.current.startOfDay(for: now)
        if let workouts = try? await healthKit.fetchWorkouts(start: start, end: now) {
            let totalSeconds = workouts.reduce(0.0) { acc, w in
                acc + w.durationSeconds
            }
            if totalSeconds > 0 {
                let minutes = totalSeconds / 60.0
                if let existing = todayWorkoutMinutes {
                    if minutes >= existing {
                        todayWorkoutMinutes = minutes
                    }
                } else {
                    todayWorkoutMinutes = minutes
                }
            }

            let kcalSum = workouts.reduce(0.0) { acc, w in
                acc + (w.totalEnergyKcal ?? 0.0)
            }
            if kcalSum > 0 {
                let kcal = kcalSum
                if let existing = todayBurnedKcal {
                    if kcal >= existing {
                        todayBurnedKcal = kcal
                    }
                } else {
                    todayBurnedKcal = kcal
                }
            }

            persistCachedMetrics()
        }
    }

    private func applySummary(_ summary: DashboardSummaryResponse) {
        if let today = summary.today {
            if let steps = today.steps {
                if todaySteps == 0 || steps >= todaySteps {
                    todaySteps = steps
                }
            }
            if let hr = today.latestHeartRate {
                if latestHeartRate == nil || hr > 0 {
                    latestHeartRate = hr
                }
            }
            if let spo2 = today.latestSpO2 {
                if latestSpO2 == nil || spo2 > 0 {
                    latestSpO2 = spo2
                }
            }
            if let sleep = today.sleepHours {
                if lastSleepHours == nil || sleep > 0 {
                    lastSleepHours = sleep
                }
            }
            if let intake = today.intakeKcal {
                if let existing = todayIntakeKcal {
                    if intake >= existing {
                        todayIntakeKcal = intake
                    }
                } else {
                    todayIntakeKcal = intake
                }
            }
            if let burned = today.burnedKcal {
                if let existing = todayBurnedKcal {
                    if burned >= existing {
                        todayBurnedKcal = burned
                    }
                } else {
                    todayBurnedKcal = burned
                }
            }
        }
        trend7d = summary.trend7d ?? []
        trend30d = summary.trend30d ?? []
        energyBalance = summary.balance
        targets = summary.targets
    }

    private func applyLifestyleSummary(_ summary: LifestyleSummaryResponse, today: String) {
        let days = summary.days.sorted { $0.date < $1.date }
        let todayDay = days.last(where: { $0.date == today }) ?? days.last

        if let steps = todayDay?.steps {
            if todaySteps == 0 || steps >= todaySteps {
                todaySteps = steps
            }
        }
        if let sleep = todayDay?.sleepHours {
            if lastSleepHours == nil || sleep > 0 {
                lastSleepHours = sleep
            }
        }
        if let intake = todayDay?.dietIntakeKcal {
            if let existing = todayIntakeKcal {
                if intake >= existing {
                    todayIntakeKcal = intake
                }
            } else {
                todayIntakeKcal = intake
            }
        }
        if let burned = todayDay?.workoutEnergyKcal {
            if let existing = todayBurnedKcal {
                if burned >= existing {
                    todayBurnedKcal = burned
                }
            } else {
                todayBurnedKcal = burned
            }
        }

        let trendDays7 = Array(days.suffix(7))
        let trendDays30 = Array(days.suffix(30))
        trend7d = trendDays7.map { day in
            DashboardTrendPoint(
                date: day.date,
                steps: day.steps,
                sleepHours: day.sleepHours,
                intakeKcal: day.dietIntakeKcal,
                burnedKcal: day.workoutEnergyKcal
            )
        }
        trend30d = trendDays30.map { day in
            DashboardTrendPoint(
                date: day.date,
                steps: day.steps,
                sleepHours: day.sleepHours,
                intakeKcal: day.dietIntakeKcal,
                burnedKcal: day.workoutEnergyKcal
            )
        }

        let weekly = trendDays7
        let weeklyAvg = weekly.isEmpty ? nil : weekly.reduce(0.0) { acc, day in
            acc + ((day.dietIntakeKcal ?? 0) - (day.workoutEnergyKcal ?? 0))
        } / Double(weekly.count)

        if let day = todayDay {
            let delta = (day.dietIntakeKcal ?? 0) - (day.workoutEnergyKcal ?? 0)
            energyBalance = EnergyBalance(
                date: day.date,
                deltaKcal: delta,
                weeklyAvgKcal: weeklyAvg,
                targetDeltaKcal: nil
            )
        }

        targets = nil
    }

    private func ensureDailyState(now: Date = Date()) {
        let key = DateFormatters.dateOnlyString(from: now)
        if currentDayKey.isEmpty {
            currentDayKey = key
        }
        if currentDayKey == key {
            return
        }
        currentDayKey = key
        resetDailyMetrics()
        persistCachedMetrics()
    }

    private func resetDailyMetrics() {
        todaySteps = 0
        latestHeartRate = nil
        latestSpO2 = nil
        lastSleepHours = nil
        todayIntakeKcal = nil
        todayBurnedKcal = nil
        todayWorkoutMinutes = nil
        todayNutritionTotals = nil
        energyBalance = nil
    }

    private func restoreCachedMetrics() {
        let todayKey = DateFormatters.dateOnlyString(from: Date())
        currentDayKey = todayKey

        guard defaults.string(forKey: Constants.dashboardCacheDateKey) == todayKey else {
            defaults.set(todayKey, forKey: Constants.dashboardCacheDateKey)
            return
        }

        if let steps = defaults.object(forKey: Constants.dashboardCacheStepsKey) as? Int {
            todaySteps = max(0, steps)
        }
        if let hr = defaults.object(forKey: Constants.dashboardCacheHeartRateKey) as? Double {
            latestHeartRate = hr
        }
        if let spo2 = defaults.object(forKey: Constants.dashboardCacheSpO2Key) as? Double {
            latestSpO2 = spo2
        }
        if let sleep = defaults.object(forKey: Constants.dashboardCacheSleepHoursKey) as? Double {
            lastSleepHours = sleep
        }
        if let intake = defaults.object(forKey: Constants.dashboardCacheIntakeKcalKey) as? Double {
            todayIntakeKcal = intake
        }
        if let burned = defaults.object(forKey: Constants.dashboardCacheBurnedKcalKey) as? Double {
            todayBurnedKcal = burned
        }
        if let minutes = defaults.object(forKey: Constants.dashboardCacheWorkoutMinutesKey) as? Double {
            todayWorkoutMinutes = minutes
        }
    }

    private func persistCachedMetrics() {
        defaults.set(currentDayKey.isEmpty ? DateFormatters.dateOnlyString(from: Date()) : currentDayKey, forKey: Constants.dashboardCacheDateKey)
        defaults.set(todaySteps, forKey: Constants.dashboardCacheStepsKey)

        if let hr = latestHeartRate {
            defaults.set(hr, forKey: Constants.dashboardCacheHeartRateKey)
        } else {
            defaults.removeObject(forKey: Constants.dashboardCacheHeartRateKey)
        }

        if let spo2 = latestSpO2 {
            defaults.set(spo2, forKey: Constants.dashboardCacheSpO2Key)
        } else {
            defaults.removeObject(forKey: Constants.dashboardCacheSpO2Key)
        }

        if let sleep = lastSleepHours {
            defaults.set(sleep, forKey: Constants.dashboardCacheSleepHoursKey)
        } else {
            defaults.removeObject(forKey: Constants.dashboardCacheSleepHoursKey)
        }

        if let intake = todayIntakeKcal {
            defaults.set(intake, forKey: Constants.dashboardCacheIntakeKcalKey)
        } else {
            defaults.removeObject(forKey: Constants.dashboardCacheIntakeKcalKey)
        }

        if let burned = todayBurnedKcal {
            defaults.set(burned, forKey: Constants.dashboardCacheBurnedKcalKey)
        } else {
            defaults.removeObject(forKey: Constants.dashboardCacheBurnedKcalKey)
        }

        if let minutes = todayWorkoutMinutes {
            defaults.set(minutes, forKey: Constants.dashboardCacheWorkoutMinutesKey)
        } else {
            defaults.removeObject(forKey: Constants.dashboardCacheWorkoutMinutesKey)
        }
    }
}
