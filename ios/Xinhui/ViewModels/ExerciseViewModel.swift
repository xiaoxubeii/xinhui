import Foundation

@MainActor
final class ExerciseViewModel: ObservableObject {
    @Published var deviceId: String = ""
    @Published var userId: String = ""
    @Published var todaySteps: Int = 0
    @Published var todayWorkoutMinutes: Double?
    @Published var todayBurnedKcal: Double?
    @Published var exercisePlan: ExercisePlanResponse?
    @Published var isLoading = false
    @Published var currentError: SyncError?

    private let healthKit = HealthKitManager()
    private let api = APIClient()

    func load() {
        deviceId = DeviceIdentifier.current
        Task { await refresh() }
    }

    func refresh() async {
        isLoading = true
        currentError = nil
        defer { isLoading = false }

        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)

        if healthKit.isAvailable {
            do {
                try await healthKit.requestAuthorization()
            } catch let error as SyncError {
                currentError = error
            } catch {
                currentError = .queryFailed(underlying: error)
            }

            if let steps = try? await healthKit.fetchDailySteps(start: startOfDay, end: now).first {
                todaySteps = steps.count
            }

            if let workouts = try? await healthKit.fetchWorkouts(start: startOfDay, end: now) {
                let totalSeconds = workouts.reduce(0.0) { $0 + $1.durationSeconds }
                todayWorkoutMinutes = totalSeconds > 0 ? totalSeconds / 60.0 : nil
                let kcal = workouts.reduce(0.0) { $0 + ($1.totalEnergyKcal ?? 0.0) }
                todayBurnedKcal = kcal > 0 ? kcal : nil
            }
        } else {
            currentError = .healthKitNotAvailable
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
            exercisePlan = try await api.fetchExercisePlan(deviceId: planOwnerId, date: today)
        } catch {
            exercisePlan = nil
        }
    }
}
