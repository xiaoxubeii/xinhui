import Foundation
import HealthKit

/// 封装所有 HealthKit 授权与查询操作。
final class HealthKitManager {
    private let store = HKHealthStore()

    var isAvailable: Bool {
        HKHealthStore.isHealthDataAvailable()
    }

    // MARK: - Authorization

    func requestAuthorization() async throws {
        guard isAvailable else { throw SyncError.healthKitNotAvailable }
        try await store.requestAuthorization(toShare: [], read: Constants.healthKitReadTypes)
    }

    // MARK: - Steps (按天聚合)

    func fetchDailySteps(start: Date, end: Date) async throws -> [SyncDailySteps] {
        guard let stepType = HKQuantityType.quantityType(forIdentifier: .stepCount) else {
            return []
        }
        let interval = DateComponents(day: 1)
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsCollectionQuery(
                quantityType: stepType,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum,
                anchorDate: Calendar.current.startOfDay(for: start),
                intervalComponents: interval
            )
            query.initialResultsHandler = { _, results, error in
                if let error { continuation.resume(throwing: SyncError.queryFailed(underlying: error)); return }
                var items: [SyncDailySteps] = []
                results?.enumerateStatistics(from: start, to: end) { stats, _ in
                    if let sum = stats.sumQuantity() {
                        let count = Int(sum.doubleValue(for: .count()))
                        let dateStr = DateFormatters.dateOnly.string(from: stats.startDate)
                        items.append(SyncDailySteps(date: dateStr, count: count))
                    }
                }
                continuation.resume(returning: items)
            }
            store.execute(query)
        }
    }

    // MARK: - Heart Rate

    func fetchHeartRateSamples(start: Date, end: Date) async throws -> [SyncHeartRateSample] {
        guard let hrType = HKQuantityType.quantityType(forIdentifier: .heartRate) else { return [] }
        let samples = try await fetchQuantitySamples(type: hrType, start: start, end: end)
        let unit = HKUnit.count().unitDivided(by: .minute())
        return samples.map { s in
            SyncHeartRateSample(
                timestamp: DateFormatters.iso8601.string(from: s.startDate),
                bpm: s.quantity.doubleValue(for: unit)
            )
        }
    }

    // MARK: - Resting Heart Rate

    func fetchRestingHeartRates(start: Date, end: Date) async throws -> [SyncRestingHeartRate] {
        guard let type = HKQuantityType.quantityType(forIdentifier: .restingHeartRate) else { return [] }
        let samples = try await fetchQuantitySamples(type: type, start: start, end: end)
        let unit = HKUnit.count().unitDivided(by: .minute())
        return samples.map { s in
            SyncRestingHeartRate(
                date: DateFormatters.dateOnly.string(from: s.startDate),
                bpm: s.quantity.doubleValue(for: unit)
            )
        }
    }

    // MARK: - SpO2

    func fetchSpO2Readings(start: Date, end: Date) async throws -> [SyncSpO2Reading] {
        guard let type = HKQuantityType.quantityType(forIdentifier: .oxygenSaturation) else { return [] }
        let samples = try await fetchQuantitySamples(type: type, start: start, end: end)
        return samples.map { s in
            SyncSpO2Reading(
                timestamp: DateFormatters.iso8601.string(from: s.startDate),
                percentage: s.quantity.doubleValue(for: .percent()) * 100.0
            )
        }
    }

    // MARK: - Sleep

    func fetchSleepSessions(start: Date, end: Date) async throws -> [SyncSleepSession] {
        guard let sleepType = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: sleepType,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]
            ) { _, results, error in
                if let error { continuation.resume(throwing: SyncError.queryFailed(underlying: error)); return }
                let sessions = (results as? [HKCategorySample] ?? []).map { sample in
                    SyncSleepSession(
                        startTime: DateFormatters.iso8601.string(from: sample.startDate),
                        endTime: DateFormatters.iso8601.string(from: sample.endDate),
                        stage: Self.sleepStageString(sample.value)
                    )
                }
                continuation.resume(returning: sessions)
            }
            store.execute(query)
        }
    }

    // MARK: - Workouts

    func fetchWorkouts(start: Date, end: Date) async throws -> [SyncWorkoutRecord] {
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: HKWorkoutType.workoutType(),
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]
            ) { _, results, error in
                if let error { continuation.resume(throwing: SyncError.queryFailed(underlying: error)); return }
                let records = (results as? [HKWorkout] ?? []).map { w in
                    SyncWorkoutRecord(
                        startTime: DateFormatters.iso8601.string(from: w.startDate),
                        endTime: DateFormatters.iso8601.string(from: w.endDate),
                        activityType: Self.workoutActivityName(w.workoutActivityType),
                        durationSeconds: w.duration,
                        totalEnergyKcal: w.totalEnergyBurned?.doubleValue(for: .kilocalorie()),
                        totalDistanceMeters: w.totalDistance?.doubleValue(for: .meter()),
                        avgHeartRate: nil,
                        maxHeartRate: nil
                    )
                }
                continuation.resume(returning: records)
            }
            store.execute(query)
        }
    }

    // MARK: - Helpers

    private func fetchQuantitySamples(
        type: HKQuantityType, start: Date, end: Date
    ) async throws -> [HKQuantitySample] {
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)
        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: type,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]
            ) { _, results, error in
                if let error { continuation.resume(throwing: SyncError.queryFailed(underlying: error)); return }
                continuation.resume(returning: results as? [HKQuantitySample] ?? [])
            }
            store.execute(query)
        }
    }

    private static func sleepStageString(_ value: Int) -> String {
        switch HKCategoryValueSleepAnalysis(rawValue: value) {
        case .inBed: return "inBed"
        case .awake: return "awake"
        case .asleepCore: return "core"
        case .asleepDeep: return "deep"
        case .asleepREM: return "rem"
        default: return "inBed"
        }
    }

    private static func workoutActivityName(_ type: HKWorkoutActivityType) -> String {
        switch type {
        case .running: return "running"
        case .cycling: return "cycling"
        case .walking: return "walking"
        case .swimming: return "swimming"
        case .hiking: return "hiking"
        case .yoga: return "yoga"
        case .functionalStrengthTraining, .traditionalStrengthTraining: return "strength_training"
        case .elliptical: return "elliptical"
        case .rowing: return "rowing"
        case .stairClimbing: return "stair_climbing"
        case .highIntensityIntervalTraining: return "hiit"
        case .dance: return "dance"
        default: return "other"
        }
    }
}
