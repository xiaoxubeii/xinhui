import Foundation
import Combine

struct WorkoutCategoryStat: Identifiable {
    let activityType: String
    let minutes: Double
    let kcal: Double

    var id: String { activityType }

    var displayName: String {
        switch activityType {
        case "running": return "跑步"
        case "cycling": return "骑行"
        case "walking": return "步行"
        case "swimming": return "游泳"
        case "hiking": return "徒步"
        case "yoga": return "瑜伽"
        case "strength_training": return "力量"
        case "elliptical": return "椭圆机"
        case "rowing": return "划船"
        case "stair_climbing": return "爬楼"
        case "hiit": return "HIIT"
        case "dance": return "舞蹈"
        default: return "其他"
        }
    }
}

@MainActor
final class ExerciseViewModel: ObservableObject {
    @Published var deviceId: String = ""
    @Published var userId: String = ""
    @Published var todaySteps: Int = 0
    @Published var todayWorkoutMinutes: Double?
    @Published var todayBurnedKcal: Double?
    @Published var workoutStats: [WorkoutCategoryStat] = []
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

                let grouped = Dictionary(grouping: workouts, by: { $0.activityType })
                workoutStats = grouped.map { type, records in
                    let seconds = records.reduce(0.0) { $0 + $1.durationSeconds }
                    let minutes = seconds / 60.0
                    let kcal = records.reduce(0.0) { $0 + ($1.totalEnergyKcal ?? 0.0) }
                    return WorkoutCategoryStat(activityType: type, minutes: minutes, kcal: kcal)
                }
                .sorted { lhs, rhs in
                    if lhs.minutes == rhs.minutes {
                        return lhs.kcal > rhs.kcal
                    }
                    return lhs.minutes > rhs.minutes
                }
                .filter { $0.minutes > 0.1 || $0.kcal > 1.0 }
            }
        } else {
            currentError = .healthKitNotAvailable
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
            exercisePlan = try await api.fetchExercisePlan(deviceId: planOwnerId, date: today)
        } catch is CancellationError {
            return
        } catch {
            exercisePlan = nil
        }
    }
}
