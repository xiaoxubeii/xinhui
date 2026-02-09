import Foundation
import HealthKit

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var serverURL: String = ""
    @Published var deviceId: String = ""
    @Published var healthKitAvailable: Bool = false
    @Published var permissionStatuses: [(name: String, granted: Bool)] = []

    func load() {
        deviceId = DeviceIdentifier.current
        healthKitAvailable = HKHealthStore.isHealthDataAvailable()

        if let saved = UserDefaults.standard.string(forKey: Constants.serverURLKey), !saved.isEmpty {
            serverURL = saved
        } else {
            serverURL = Constants.defaultBaseURL.absoluteString
        }

        refreshPermissions()
    }

    func saveServerURL() {
        let trimmed = serverURL.trimmingCharacters(in: .whitespacesAndNewlines)
        UserDefaults.standard.set(trimmed, forKey: Constants.serverURLKey)
    }

    func refreshPermissions() {
        guard healthKitAvailable else { return }
        let store = HKHealthStore()
        let types: [(String, HKObjectType?)] = [
            ("步数", HKQuantityType.quantityType(forIdentifier: .stepCount)),
            ("心率", HKQuantityType.quantityType(forIdentifier: .heartRate)),
            ("静息心率", HKQuantityType.quantityType(forIdentifier: .restingHeartRate)),
            ("血氧", HKQuantityType.quantityType(forIdentifier: .oxygenSaturation)),
            ("睡眠", HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)),
            ("运动", HKWorkoutType.workoutType()),
        ]
        permissionStatuses = types.compactMap { name, type in
            guard let type else { return nil }
            let status = store.authorizationStatus(for: type)
            return (name: name, granted: status == .sharingAuthorized || status != .notDetermined)
        }
    }
}
