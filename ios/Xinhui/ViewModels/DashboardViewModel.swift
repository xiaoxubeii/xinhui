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
    @Published var trend7d: [DashboardTrendPoint] = []
    @Published var trend30d: [DashboardTrendPoint] = []
    @Published var energyBalance: EnergyBalance?
    @Published var targets: HealthTargets?
    @Published var exercisePlan: ExercisePlanResponse?
    @Published var nutritionPlan: NutritionPlanResponse?
    @Published var dashboardError: String = ""

    private let healthKit = HealthKitManager()
    private let api = APIClient()

    func load() {
        deviceId = DeviceIdentifier.current
        lastSyncDate = UserDefaults.standard.object(forKey: Constants.lastSyncDateKey) as? Date
        Task { await refreshTodayData() }
    }

    func refreshTodayData() async {
        dashboardError = ""
        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)

        if healthKit.isAvailable {
            do {
                try await healthKit.requestAuthorization()
            } catch {
                dashboardError = "HealthKit 授权失败"
            }
            // Steps
            if let steps = try? await healthKit.fetchDailySteps(start: startOfDay, end: now).first {
                todaySteps = steps.count
            }

            // Heart rate (latest)
            if let hr = try? await healthKit.fetchHeartRateSamples(start: startOfDay, end: now).last {
                latestHeartRate = hr.bpm
            }

            // SpO2 (latest)
            if let spo2 = try? await healthKit.fetchSpO2Readings(start: startOfDay, end: now).last {
                latestSpO2 = spo2.percentage
            }

            // Sleep (last night)
            let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: startOfDay)!
            if let sessions = try? await healthKit.fetchSleepSessions(start: yesterday, end: startOfDay) {
                let totalSeconds = sessions.reduce(0.0) { acc, s in
                    guard let start = ISO8601DateFormatter().date(from: s.startTime),
                          let end = ISO8601DateFormatter().date(from: s.endTime) else { return acc }
                    return acc + end.timeIntervalSince(start)
                }
                if totalSeconds > 0 {
                    lastSleepHours = totalSeconds / 3600.0
                }
            }

            // Workout energy (today)
            if let workouts = try? await healthKit.fetchWorkouts(start: startOfDay, end: now) {
                let kcal = workouts.reduce(0.0) { acc, w in
                    acc + (w.totalEnergyKcal ?? 0.0)
                }
                todayBurnedKcal = kcal > 0 ? kcal : nil
            }
        }

        // Diet intake (today, from backend)
        do {
            let today = DateFormatters.dateOnly.string(from: now)
            let summary = try await api.fetchDietSummary(deviceId: deviceId, start: today, end: today)
            todayIntakeKcal = summary.totals.caloriesKcal
        } catch {
            if todayIntakeKcal == nil {
                todayIntakeKcal = nil
            }
        }

        // Dashboard summary (trend + targets + balance)
        do {
            let today = DateFormatters.dateOnly.string(from: now)
            let start30 = DateFormatters.dateOnly.string(from: Calendar.current.date(byAdding: .day, value: -29, to: startOfDay) ?? startOfDay)
            let summary = try await api.fetchDashboardSummary(deviceId: deviceId, start: start30, end: today)
            applySummary(summary)
        } catch {
            dashboardError = "Dashboard 汇总数据获取失败"
        }

        // Plans (exercise & nutrition)
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
