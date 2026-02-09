import Foundation
import Combine

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published var lastSyncDate: Date?
    @Published var deviceId: String = ""
    @Published var todaySteps: Int = 0
    @Published var latestHeartRate: Double?
    @Published var latestSpO2: Double?
    @Published var lastSleepHours: Double?
    @Published var todayIntakeKcal: Double?
    @Published var todayBurnedKcal: Double?

    private let healthKit = HealthKitManager()
    private let api = APIClient()

    func load() {
        deviceId = DeviceIdentifier.current
        lastSyncDate = UserDefaults.standard.object(forKey: Constants.lastSyncDateKey) as? Date
        Task { await refreshTodayData() }
    }

    func refreshTodayData() async {
        guard healthKit.isAvailable else { return }
        do {
            try await healthKit.requestAuthorization()
        } catch {
            return
        }

        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)

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

        // Diet intake (today, from backend)
        do {
            let today = DateFormatters.dateOnly.string(from: now)
            let summary = try await api.fetchDietSummary(deviceId: deviceId, start: today, end: today)
            todayIntakeKcal = summary.totals.caloriesKcal
        } catch {
            todayIntakeKcal = nil
        }
    }
}
