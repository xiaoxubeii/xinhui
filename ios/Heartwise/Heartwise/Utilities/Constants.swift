import Foundation
import HealthKit

enum Constants {
    static let defaultBaseURL = URL(string: "http://localhost:8000/api")!
    static let syncTimeoutInterval: TimeInterval = 60
    static let maxPayloadBytes = 5 * 1024 * 1024 // 5 MB
    static let defaultSyncDays = 30

    static let serverURLKey = "xinhui_server_url"
    static let lastSyncDateKey = "xinhui_last_sync"
    static let deviceIDKey = "xinhui_device_id"

    /// HealthKit 读取权限集合
    static let healthKitReadTypes: Set<HKObjectType> = {
        var types = Set<HKObjectType>()
        if let stepCount = HKQuantityType.quantityType(forIdentifier: .stepCount) {
            types.insert(stepCount)
        }
        if let heartRate = HKQuantityType.quantityType(forIdentifier: .heartRate) {
            types.insert(heartRate)
        }
        if let restingHR = HKQuantityType.quantityType(forIdentifier: .restingHeartRate) {
            types.insert(restingHR)
        }
        if let spo2 = HKQuantityType.quantityType(forIdentifier: .oxygenSaturation) {
            types.insert(spo2)
        }
        if let sleep = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) {
            types.insert(sleep)
        }
        types.insert(HKWorkoutType.workoutType())
        return types
    }()
}
