import Foundation

protocol AgentService {
    func reply(
        to userText: String,
        context: AgentContext?,
        attachments: [AgentAttachment],
        history: [AgentMessage]
    ) async throws -> String
}

final class RemoteAgentService: AgentService {
    private let api: APIClient

    init(api: APIClient = APIClient()) {
        self.api = api
    }

    func reply(
        to userText: String,
        context: AgentContext?,
        attachments: [AgentAttachment],
        history: [AgentMessage]
    ) async throws -> String {
        var historyMessages = history
        if let last = historyMessages.last, last.role == .user, last.text == userText {
            historyMessages.removeLast()
        }

        let payloadHistory = historyMessages.map {
            AgentAskMessage(role: $0.role.rawValue, content: $0.text)
        }

        let payloadAttachments: [AgentAskAttachment] = attachments.compactMap { attachment in
            guard let artifactId = attachment.artifactId else { return nil }
            return AgentAskAttachment(
                id: artifactId,
                filename: attachment.filename,
                contentType: attachment.contentType,
                sizeBytes: attachment.sizeBytes,
                category: attachment.category.rawValue
            )
        }

        let payloadContext: AgentAskContext? = {
            if context != nil || !payloadAttachments.isEmpty {
                return AgentAskContext(context: context, attachments: payloadAttachments)
            }
            return nil
        }()

        let payload = AgentAskRequest(
            question: userText,
            page: nil,
            context: payloadContext,
            history: payloadHistory
        )

        let response = try await api.askAgent(payload)
        return response.answer
    }
}

final class MockAgentService: AgentService {
    func reply(
        to userText: String,
        context: AgentContext?,
        attachments: [AgentAttachment],
        history: [AgentMessage]
    ) async throws -> String {
        let text = userText.trimmingCharacters(in: .whitespacesAndNewlines)
        let lower = text.lowercased()
        let disclaimer = "（仅供健康管理参考，不构成医疗建议。）"
        let attachmentNote = attachments.isEmpty ? "" : "我已收到 \(attachments.count) 个附件。"

        guard !text.isEmpty else {
            return "你可以直接问我：例如“我今天步数多少？”\(attachmentNote)\(disclaimer)"
        }

        if lower.contains("你好") || lower.contains("在吗") || lower.contains("hello") {
            return """
            你好！我可以根据你的健康摘要帮你解读今天的状态，也可以回答步数、心率、血氧、睡眠、消耗、摄入等问题。
            \(attachmentNote)

            你也可以试试：
            - 我今天步数多少？
            - 昨晚睡得怎么样？
            - 给我一个今日建议
            \(disclaimer)
            """
        }

        if lower.contains("摘要") || lower.contains("总结") || lower.contains("概况") || lower.contains("状况") {
            if let context {
                return "这是你当前的健康摘要：\n\n\(context.summaryText)\n\n你想重点看哪一项？\(disclaimer)"
            }
            return "我这条对话没有拿到你的健康摘要。你可以打开“附带健康摘要”，再点顶部“刷新摘要”，并在系统弹窗里允许 HealthKit 权限。\n\n拿到摘要后我就能用具体数值回答你。\(disclaimer)"
        }

        // Steps
        if lower.contains("步数") || lower.contains("走") || lower.contains("步") {
            if let context {
                let steps = context.todaySteps
                let advice: String
                if steps < 3000 {
                    advice = "今天活动量偏少，可以考虑分 2-3 次快走，每次 10-15 分钟。"
                } else if steps < 8000 {
                    advice = "今天步数不错，继续保持，晚饭后散步 10-20 分钟会更舒服。"
                } else {
                    advice = "今天活动量很棒，注意补水与拉伸。"
                }
                return "你今天的步数是 \(steps) 步。\n\(advice)\n\(disclaimer)"
            }
            return "我这条对话没有收到健康摘要，所以没法给出具体步数。你可以打开“附带健康摘要”，再点顶部“刷新摘要”并授权 HealthKit。\n\(disclaimer)"
        }

        // Sleep
        if lower.contains("睡") || lower.contains("睡眠") {
            if let context, let hours = context.lastSleepHours {
                let advice: String
                if hours < 6 {
                    advice = "昨晚睡眠偏少，今天尽量避免高强度训练，适当午休 10-20 分钟。"
                } else if hours < 7 {
                    advice = "睡眠略偏少，今晚尽量提前入睡，睡前减少咖啡因与屏幕刺激。"
                } else {
                    advice = "睡眠时长不错，继续保持稳定作息。"
                }
                return String(format: "昨晚你的睡眠时长约为 %.1f 小时。\n%@\n%@", hours, advice, disclaimer)
            }
            if context != nil {
                return "我拿到摘要了，但没取到昨晚睡眠数据（可能未记录或权限未开）。你可以在“健康”App里确认是否有睡眠记录。\n\(disclaimer)"
            }
            return "我这条对话没有收到健康摘要，所以没法给出睡眠时长。你可以打开“附带健康摘要”，再点顶部“刷新摘要”并授权 HealthKit。\n\(disclaimer)"
        }

        // Heart rate
        if lower.contains("心率") || lower.contains("心跳") || lower.contains("bpm") {
            if let context, let hr = context.latestHeartRate {
                let advice: String
                if hr >= 110 {
                    advice = "当前心率偏高（若你在静息状态），建议先休息、补水，观察是否回落。"
                } else if hr >= 90 {
                    advice = "心率略高，可能与活动、压力、咖啡因有关。"
                } else {
                    advice = "心率看起来在常见范围内。"
                }
                return String(format: "你最新的心率约为 %.0f bpm。\n%@\n%@", hr, advice, disclaimer)
            }
            if context != nil {
                return "我拿到摘要了，但暂时没有心率样本（可能今天没有测量记录或权限未开）。\n\(disclaimer)"
            }
            return "我这条对话没有收到健康摘要，所以没法给出心率数值。你可以打开“附带健康摘要”，再点顶部“刷新摘要”并授权 HealthKit。\n\(disclaimer)"
        }

        // SpO2
        if lower.contains("血氧") || lower.contains("spo2") || lower.contains("氧饱和") {
            if let context, let o2 = context.latestSpO2 {
                let advice: String
                if o2 < 94 {
                    advice = "血氧偏低（若测量准确且持续如此），建议复测并关注呼吸情况，必要时咨询专业医生。"
                } else if o2 < 96 {
                    advice = "血氧略偏低，建议复测并确保测量姿势正确。"
                } else {
                    advice = "血氧看起来不错。"
                }
                return String(format: "你最新的血氧约为 %.0f%%。\n%@\n%@", o2, advice, disclaimer)
            }
            if context != nil {
                return "我拿到摘要了，但暂时没有血氧读数（可能今天没有测量记录或权限未开）。\n\(disclaimer)"
            }
            return "我这条对话没有收到健康摘要，所以没法给出血氧数值。你可以打开“附带健康摘要”，再点顶部“刷新摘要”并授权 HealthKit。\n\(disclaimer)"
        }

        // Calories burned / workouts
        if lower.contains("消耗") || lower.contains("运动") || lower.contains("燃烧") || lower.contains("卡路里") {
            if let context, let burned = context.todayBurnedKcal {
                return String(format: "你今天记录到的运动消耗约为 %.0f kcal。\n如果你想提高消耗，可以在安全范围内增加步行/慢跑时长或加入力量训练。\n%@", burned, disclaimer)
            }
            if context != nil {
                return "我拿到摘要了，但今天可能没有运动记录，或未能读取到能量消耗。\n\(disclaimer)"
            }
            return "我这条对话没有收到健康摘要，所以没法给出运动消耗。你可以打开“附带健康摘要”，再点顶部“刷新摘要”并授权 HealthKit。\n\(disclaimer)"
        }

        // Intake
        if lower.contains("摄入") || lower.contains("饮食") || lower.contains("吃") {
            if let context, let intake = context.todayIntakeKcal {
                return String(format: "你今天记录到的摄入约为 %.0f kcal。\n如果想更精确，可以在“饮食”里继续拍照记录。\n%@", intake, disclaimer)
            }
            if context != nil {
                return "我还没拿到摄入数据（可能后端未连接或你还没记录饮食）。你可以去“饮食”里拍照记录一餐。\n\(disclaimer)"
            }
            return "我这条对话没有收到健康摘要，所以没法给出摄入数值。你可以打开“附带健康摘要”，再点顶部“刷新摘要”；另外也可以去“饮食”里先记录一餐。\n\(disclaimer)"
        }

        // General advice
        if lower.contains("建议") || lower.contains("怎么办") || lower.contains("怎么做") || lower.contains("计划") {
            if let context {
                var tips: [String] = []
                if context.todaySteps < 6000 {
                    tips.append("今天步数偏少：晚饭后快走 15-20 分钟。")
                } else {
                    tips.append("活动量不错：注意补水与拉伸。")
                }
                if let sleep = context.lastSleepHours, sleep < 7 {
                    tips.append("睡眠偏少：今晚尽量提前 30 分钟入睡。")
                }
                if let intake = context.todayIntakeKcal,
                   let burned = context.todayBurnedKcal,
                   intake - burned > 600 {
                    tips.append("摄入明显高于消耗：晚间饮食可适当清淡，避免高糖高油。")
                }
                if tips.isEmpty {
                    tips.append("先保持均衡饮食与规律作息，再结合你的目标调整运动强度。")
                }
                return "给你一个今天的小建议：\n- " + tips.joined(separator: "\n- ") + "\n" + disclaimer
            }
            return "我可以给建议，但这条对话没有收到健康摘要。你可以打开“附带健康摘要”，再点顶部“刷新摘要”并授权 HealthKit。\n\(disclaimer)"
        }

        // Fallback
        if let context {
            return "我明白了。你也可以更具体一点，比如“结合今天的步数和睡眠，给我一个运动建议”。\n\n当前摘要：\n\(context.summaryText)\n\n\(disclaimer)"
        }
        return "我明白了。你可以打开“附带健康摘要”，点顶部“刷新摘要”授权 HealthKit，然后再问我步数/睡眠/心率/血氧/运动/饮食等问题。\n\(disclaimer)"
    }
}
