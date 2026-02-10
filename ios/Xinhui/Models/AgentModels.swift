import Foundation

enum AgentRole: String, Codable {
    case user
    case assistant
}

enum ArtifactCategory: String, Codable, CaseIterable {
    case cpetReport = "cpet_report"
    case exerciseData = "exercise_data"
    case healthData = "health_data"
    case dietData = "diet_data"
    case labReport = "lab_report"
    case imagingReport = "imaging_report"
    case other
}

struct ArtifactUploadResponse: Codable, Equatable {
    let id: String
    let category: ArtifactCategory
    let title: String?
    let filename: String
    let contentType: String
    let sizeBytes: Int
    let sha256: String
    let createdAt: String
    let extractedPreview: String?
    let hasParsedJson: Bool?

    enum CodingKeys: String, CodingKey {
        case id
        case category
        case title
        case filename
        case contentType = "content_type"
        case sizeBytes = "size_bytes"
        case sha256
        case createdAt = "created_at"
        case extractedPreview = "extracted_preview"
        case hasParsedJson = "has_parsed_json"
    }
}

struct AgentAttachment: Identifiable, Codable, Equatable {
    let id: UUID
    var artifactId: String?
    var filename: String
    var contentType: String
    var sizeBytes: Int
    var category: ArtifactCategory
    var thumbnailData: Data?
    var isUploading: Bool
    var error: String?

    var isImage: Bool {
        contentType.lowercased().hasPrefix("image/")
    }
}

struct AgentMessage: Identifiable, Codable, Equatable {
    let id: UUID
    let role: AgentRole
    let text: String
    let timestamp: Date
    let attachments: [AgentAttachment]

    init(
        id: UUID = UUID(),
        role: AgentRole,
        text: String,
        timestamp: Date = Date(),
        attachments: [AgentAttachment] = []
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.timestamp = timestamp
        self.attachments = attachments
    }
}

struct AgentContext: Codable, Equatable {
    let deviceId: String
    let lastSyncDate: Date?
    let generatedAt: Date
    let todaySteps: Int
    let latestHeartRate: Double?
    let latestSpO2: Double?
    let lastSleepHours: Double?
    let todayBurnedKcal: Double?
    let todayIntakeKcal: Double?

    var summaryText: String {
        var lines: [String] = []

        let deviceShort = deviceId.count > 8 ? String(deviceId.prefix(8)) + "..." : deviceId
        lines.append("设备 ID: \(deviceShort)")

        if let lastSyncDate {
            lines.append("上次同步: \(DateFormatters.displayDateTime.string(from: lastSyncDate))")
        } else {
            lines.append("上次同步: --")
        }

        lines.append("今日步数: \(todaySteps) 步")

        if let latestHeartRate {
            lines.append(String(format: "最新心率: %.0f bpm", latestHeartRate))
        } else {
            lines.append("最新心率: --")
        }

        if let latestSpO2 {
            lines.append(String(format: "最新血氧: %.0f%%", latestSpO2))
        } else {
            lines.append("最新血氧: --")
        }

        if let lastSleepHours {
            lines.append(String(format: "昨晚睡眠: %.1f 小时", lastSleepHours))
        } else {
            lines.append("昨晚睡眠: --")
        }

        if let todayBurnedKcal {
            lines.append(String(format: "今日消耗: %.0f kcal", todayBurnedKcal))
        } else {
            lines.append("今日消耗: --")
        }

        if let todayIntakeKcal {
            lines.append(String(format: "今日摄入: %.0f kcal", todayIntakeKcal))
        } else {
            lines.append("今日摄入: --")
        }

        lines.append("生成时间: \(DateFormatters.displayDateTime.string(from: generatedAt))")
        return lines.joined(separator: "\n")
    }
}

struct AgentAskMessage: Codable, Equatable {
    let role: String
    let content: String
}

struct AgentAskAttachment: Codable, Equatable {
    let id: String
    let filename: String
    let contentType: String
    let sizeBytes: Int
    let category: String

    enum CodingKeys: String, CodingKey {
        case id
        case filename
        case contentType = "content_type"
        case sizeBytes = "size_bytes"
        case category
    }
}

struct AgentAskContext: Codable, Equatable {
    let deviceId: String?
    let generatedAt: String?
    let lastSyncAt: String?
    let todaySteps: Int?
    let latestHeartRate: Double?
    let latestSpO2: Double?
    let lastSleepHours: Double?
    let todayBurnedKcal: Double?
    let todayIntakeKcal: Double?
    let summary: String?
    let attachments: [AgentAskAttachment]?

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case generatedAt = "generated_at"
        case lastSyncAt = "last_sync_at"
        case todaySteps = "today_steps"
        case latestHeartRate = "latest_heart_rate"
        case latestSpO2 = "latest_spo2"
        case lastSleepHours = "last_sleep_hours"
        case todayBurnedKcal = "today_burned_kcal"
        case todayIntakeKcal = "today_intake_kcal"
        case summary
        case attachments
    }

    init(context: AgentContext?, attachments: [AgentAskAttachment]?) {
        if let context {
            deviceId = context.deviceId
            generatedAt = DateFormatters.iso8601String(from: context.generatedAt)
            if let lastSync = context.lastSyncDate {
                lastSyncAt = DateFormatters.iso8601String(from: lastSync)
            } else {
                lastSyncAt = nil
            }
            todaySteps = context.todaySteps
            latestHeartRate = context.latestHeartRate
            latestSpO2 = context.latestSpO2
            lastSleepHours = context.lastSleepHours
            todayBurnedKcal = context.todayBurnedKcal
            todayIntakeKcal = context.todayIntakeKcal
            summary = context.summaryText
        } else {
            deviceId = nil
            generatedAt = nil
            lastSyncAt = nil
            todaySteps = nil
            latestHeartRate = nil
            latestSpO2 = nil
            lastSleepHours = nil
            todayBurnedKcal = nil
            todayIntakeKcal = nil
            summary = nil
        }
        self.attachments = attachments
    }
}

struct AgentAskRequest: Codable, Equatable {
    let question: String
    let page: String?
    let context: AgentAskContext?
    let history: [AgentAskMessage]
}

struct AgentAskResponse: Codable, Equatable {
    let answer: String
    let model: String
    let start: Double?
    let end: Double?
}
