import Foundation

/// 编排 HealthKit 查询 → 组装 payload → 上传到后端。
final class SyncCoordinator {
    private let healthKit = HealthKitManager()
    private let apiClient: APIClient

    init(apiClient: APIClient = APIClient()) {
        self.apiClient = apiClient
    }

    /// 执行一次完整同步。
    func performSync(
        dataTypes: Set<HealthDataType>,
        dateRange: ClosedRange<Date>,
        onProgress: @escaping (SyncProgress) -> Void
    ) async throws -> HealthSyncResponse {
        guard healthKit.isAvailable else { throw SyncError.healthKitNotAvailable }

        var progress = SyncProgress()

        // 1. 授权
        try await healthKit.requestAuthorization()

        let start = dateRange.lowerBound
        let end = dateRange.upperBound

        // 2. 逐类型查询
        var payload = HealthSyncRequest(
            deviceId: DeviceIdentifier.current,
            syncStart: DateFormatters.iso8601String(from: start),
            syncEnd: DateFormatters.iso8601String(from: end)
        )

        for dataType in HealthDataType.allCases where dataTypes.contains(dataType) {
            progress.currentType = dataType
            progress.phase = .querying
            onProgress(progress)

            switch dataType {
            case .steps:
                payload.dailySteps = try await healthKit.fetchDailySteps(start: start, end: end)
            case .heartRate:
                payload.heartRateSamples = try await healthKit.fetchHeartRateSamples(start: start, end: end)
            case .restingHeartRate:
                payload.restingHeartRates = try await healthKit.fetchRestingHeartRates(start: start, end: end)
            case .spo2:
                payload.spo2Readings = try await healthKit.fetchSpO2Readings(start: start, end: end)
            case .sleep:
                payload.sleepSessions = try await healthKit.fetchSleepSessions(start: start, end: end)
            case .workouts:
                payload.workouts = try await healthKit.fetchWorkouts(start: start, end: end)
            }

            progress.completedTypes.insert(dataType)
            onProgress(progress)
        }

        // 3. 上传
        progress.phase = .uploading
        progress.currentType = nil
        onProgress(progress)

        let response = try await apiClient.syncHealthData(payload)

        // 4. 记录最后同步时间
        UserDefaults.standard.set(Date(), forKey: Constants.lastSyncDateKey)

        progress.phase = .done
        onProgress(progress)

        return response
    }
}

@MainActor
final class AutoSyncManager {
    static let shared = AutoSyncManager()

    private let coordinator = SyncCoordinator()
    private var syncTask: Task<Void, Never>?

    private init() {}

    func triggerIfEnabled(force: Bool = false) {
        guard UserDefaults.standard.bool(forKey: Constants.autoSyncEnabledKey) else { return }
        if !force, !shouldRunNow() { return }
        guard syncTask == nil else { return }

        UserDefaults.standard.set(Date(), forKey: Constants.lastAutoSyncAttemptDateKey)
        UserDefaults.standard.removeObject(forKey: Constants.lastAutoSyncErrorKey)

        let now = Date()
        let start = Calendar.current.date(byAdding: .day, value: -Constants.autoSyncDays, to: now) ?? now

        syncTask = Task {
            defer { syncTask = nil }
            do {
                _ = try await coordinator.performSync(
                    dataTypes: Set(HealthDataType.allCases),
                    dateRange: start...now,
                    onProgress: { _ in }
                )
                UserDefaults.standard.set(Date(), forKey: Constants.lastAutoSyncSuccessDateKey)
            } catch {
                UserDefaults.standard.set(error.localizedDescription, forKey: Constants.lastAutoSyncErrorKey)
            }
        }
    }

    private func shouldRunNow() -> Bool {
        if let lastAttempt = UserDefaults.standard.object(forKey: Constants.lastAutoSyncAttemptDateKey) as? Date {
            return Date().timeIntervalSince(lastAttempt) >= Constants.autoSyncMinInterval
        }
        return true
    }
}
