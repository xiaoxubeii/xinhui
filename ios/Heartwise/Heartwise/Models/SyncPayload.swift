import Foundation

// MARK: - Request Models (匹配后端 HealthSyncRequest)

struct SyncDailySteps: Codable {
    let date: String
    let count: Int
}

struct SyncHeartRateSample: Codable {
    let timestamp: String
    let bpm: Double
}

struct SyncRestingHeartRate: Codable {
    let date: String
    let bpm: Double
}

struct SyncSpO2Reading: Codable {
    let timestamp: String
    let percentage: Double
}

struct SyncSleepSession: Codable {
    let startTime: String
    let endTime: String
    let stage: String

    enum CodingKeys: String, CodingKey {
        case startTime = "start_time"
        case endTime = "end_time"
        case stage
    }
}

struct SyncWorkoutRecord: Codable {
    let startTime: String
    let endTime: String
    let activityType: String
    let durationSeconds: Double
    let totalEnergyKcal: Double?
    let totalDistanceMeters: Double?
    let avgHeartRate: Double?
    let maxHeartRate: Double?

    enum CodingKeys: String, CodingKey {
        case startTime = "start_time"
        case endTime = "end_time"
        case activityType = "activity_type"
        case durationSeconds = "duration_seconds"
        case totalEnergyKcal = "total_energy_kcal"
        case totalDistanceMeters = "total_distance_meters"
        case avgHeartRate = "avg_heart_rate"
        case maxHeartRate = "max_heart_rate"
    }
}

struct HealthSyncRequest: Codable {
    let deviceId: String
    let syncStart: String
    let syncEnd: String
    var dailySteps: [SyncDailySteps] = []
    var heartRateSamples: [SyncHeartRateSample] = []
    var restingHeartRates: [SyncRestingHeartRate] = []
    var spo2Readings: [SyncSpO2Reading] = []
    var sleepSessions: [SyncSleepSession] = []
    var workouts: [SyncWorkoutRecord] = []

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case syncStart = "sync_start"
        case syncEnd = "sync_end"
        case dailySteps = "daily_steps"
        case heartRateSamples = "heart_rate_samples"
        case restingHeartRates = "resting_heart_rates"
        case spo2Readings = "spo2_readings"
        case sleepSessions = "sleep_sessions"
        case workouts
    }
}

// MARK: - Response Model (匹配后端 HealthSyncResponse)

struct HealthSyncResponse: Codable {
    let status: String
    let message: String
    let receivedCounts: [String: Int]
    let syncId: String

    enum CodingKeys: String, CodingKey {
        case status, message
        case receivedCounts = "received_counts"
        case syncId = "sync_id"
    }
}
