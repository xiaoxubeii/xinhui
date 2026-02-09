import Foundation

/// 用户可选择同步的数据类型
enum HealthDataType: String, CaseIterable, Identifiable {
    case steps = "步数"
    case heartRate = "心率"
    case restingHeartRate = "静息心率"
    case spo2 = "血氧"
    case sleep = "睡眠"
    case workouts = "运动"

    var id: String { rawValue }

    var iconName: String {
        switch self {
        case .steps: return "figure.walk"
        case .heartRate: return "heart.fill"
        case .restingHeartRate: return "heart.text.square"
        case .spo2: return "lungs.fill"
        case .sleep: return "bed.double.fill"
        case .workouts: return "figure.run"
        }
    }
}

/// 同步进度
struct SyncProgress {
    var currentType: HealthDataType?
    var completedTypes: Set<HealthDataType> = []
    var phase: Phase = .idle

    enum Phase: String {
        case idle = "就绪"
        case querying = "正在读取数据"
        case uploading = "正在上传"
        case done = "完成"
        case failed = "失败"
    }

    var fractionCompleted: Double {
        let total = Double(HealthDataType.allCases.count + 1) // +1 for upload
        let done = Double(completedTypes.count) + (phase == .done ? 1.0 : 0.0)
        return min(done / total, 1.0)
    }
}
