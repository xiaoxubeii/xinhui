import Foundation
import Combine
import UniformTypeIdentifiers

@MainActor
final class AgentChatViewModel: ObservableObject {
    @Published var messages: [AgentMessage] = []
    @Published var inputText: String = ""
    @Published var isSending: Bool = false

    @Published var context: AgentContext?
    @Published var isLoadingContext: Bool = false
    @Published var contextError: String?
    @Published var attachments: [AgentAttachment] = []
    @Published var attachmentError: String?

    private let healthKit = HealthKitManager()
    private let api = APIClient()
    private let service: any AgentService
    private var didLoadContext = false

    init(service: any AgentService = RemoteAgentService()) {
        self.service = service
        self.messages = [
            AgentMessage(
                role: .assistant,
                text: "你好，我是智问。你可以问我步数、睡眠、心率、血氧、消耗、摄入等问题；也可以让我基于摘要给你一个今日建议。"
            ),
        ]
    }

    func loadContextIfNeeded() async {
        guard !didLoadContext else { return }
        await loadContext(force: false)
    }

    func loadContext(force: Bool) async {
        if didLoadContext && !force { return }
        didLoadContext = true

        isLoadingContext = true
        contextError = nil
        defer { isLoadingContext = false }

        guard healthKit.isAvailable else {
            context = nil
            contextError = "HealthKit 不可用"
            return
        }

        do {
            try await healthKit.requestAuthorization()
        } catch {
            context = nil
            contextError = error.localizedDescription
            return
        }

        let deviceId = DeviceIdentifier.current
        let lastSyncDate = UserDefaults.standard.object(forKey: Constants.lastSyncDateKey) as? Date

        let now = Date()
        let startOfDay = Calendar.current.startOfDay(for: now)

        var todaySteps = 0
        var latestHeartRate: Double?
        var latestSpO2: Double?
        var lastSleepHours: Double?
        var todayBurnedKcal: Double?
        var todayIntakeKcal: Double?

        if let steps = try? await healthKit.fetchDailySteps(start: startOfDay, end: now).first {
            todaySteps = steps.count
        }

        if let hr = try? await healthKit.fetchHeartRateSamples(start: startOfDay, end: now).last {
            latestHeartRate = hr.bpm
        }

        if let spo2 = try? await healthKit.fetchSpO2Readings(start: startOfDay, end: now).last {
            latestSpO2 = spo2.percentage
        }

        let yesterday = Calendar.current.date(byAdding: .day, value: -1, to: startOfDay)!
        if let sessions = try? await healthKit.fetchSleepSessions(start: yesterday, end: startOfDay) {
            let totalSeconds = sessions.reduce(0.0) { acc, s in
                guard let start = DateFormatters.iso8601.date(from: s.startTime),
                      let end = DateFormatters.iso8601.date(from: s.endTime) else { return acc }
                return acc + end.timeIntervalSince(start)
            }
            if totalSeconds > 0 {
                lastSleepHours = totalSeconds / 3600.0
            }
        }

        if let workouts = try? await healthKit.fetchWorkouts(start: startOfDay, end: now) {
            let kcal = workouts.reduce(0.0) { acc, w in
                acc + (w.totalEnergyKcal ?? 0.0)
            }
            todayBurnedKcal = kcal > 0 ? kcal : nil
        }

        do {
            let today = DateFormatters.dateOnly.string(from: now)
            let summary = try await api.fetchDietSummary(deviceId: deviceId, start: today, end: today)
            todayIntakeKcal = summary.totals.caloriesKcal
        } catch {
            todayIntakeKcal = nil
        }

        context = AgentContext(
            deviceId: deviceId,
            lastSyncDate: lastSyncDate,
            generatedAt: now,
            todaySteps: todaySteps,
            latestHeartRate: latestHeartRate,
            latestSpO2: latestSpO2,
            lastSleepHours: lastSleepHours,
            todayBurnedKcal: todayBurnedKcal,
            todayIntakeKcal: todayIntakeKcal
        )
    }

    func send(includeContext: Bool) async {
        let trimmed = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        if attachments.contains(where: { $0.isUploading }) {
            attachmentError = "附件正在上传，请稍后再发送。"
            return
        }

        let readyAttachments = attachments.filter { $0.artifactId != nil }
        let messageText = trimmed.isEmpty && !readyAttachments.isEmpty ? "请查看附件" : trimmed
        guard !messageText.isEmpty else { return }
        guard !isSending else { return }

        inputText = ""
        messages.append(AgentMessage(role: .user, text: messageText, attachments: readyAttachments))
        attachments.removeAll()

        isSending = true
        defer { isSending = false }

        let ctx = includeContext ? context : nil
        do {
            let reply = try await service.reply(
                to: messageText,
                context: ctx,
                attachments: readyAttachments,
                history: messages
            )
            messages.append(AgentMessage(role: .assistant, text: reply))
        } catch {
            messages.append(AgentMessage(role: .assistant, text: "抱歉，我暂时无法回答这个问题：\(error.localizedDescription)"))
        }
    }

    func addAttachment(
        data: Data,
        filename: String,
        contentType: String,
        category: ArtifactCategory = .other,
        thumbnailData: Data? = nil
    ) async {
        let attachmentId = UUID()
        let initial = AgentAttachment(
            id: attachmentId,
            artifactId: nil,
            filename: filename,
            contentType: contentType,
            sizeBytes: data.count,
            category: category,
            thumbnailData: thumbnailData,
            isUploading: true,
            error: nil
        )
        attachments.append(initial)

        do {
            let response = try await api.uploadArtifact(
                category: category,
                title: filename,
                attachSessionId: nil,
                fileData: data,
                filename: filename,
                contentType: contentType
            )
            updateAttachment(id: attachmentId) { item in
                var next = item
                next.artifactId = response.id
                next.isUploading = false
                next.error = nil
                return next
            }
        } catch {
            updateAttachment(id: attachmentId) { item in
                var next = item
                next.isUploading = false
                next.error = error.localizedDescription
                return next
            }
            attachmentError = "附件上传失败：\(error.localizedDescription)"
        }
    }

    func addFileAttachment(url: URL) async {
        let shouldStop = url.startAccessingSecurityScopedResource()
        defer { if shouldStop { url.stopAccessingSecurityScopedResource() } }
        do {
            let data = try Data(contentsOf: url)
            let filename = url.lastPathComponent.isEmpty
                ? "file-\(Int(Date().timeIntervalSince1970))"
                : url.lastPathComponent
            let contentType = mimeType(for: url)
            await addAttachment(data: data, filename: filename, contentType: contentType, thumbnailData: nil)
        } catch {
            attachmentError = "读取文件失败：\(error.localizedDescription)"
        }
    }

    func removeAttachment(id: UUID) {
        attachments.removeAll { $0.id == id }
    }

    private func updateAttachment(id: UUID, transform: (AgentAttachment) -> AgentAttachment) {
        if let index = attachments.firstIndex(where: { $0.id == id }) {
            attachments[index] = transform(attachments[index])
        }
    }

    private func mimeType(for url: URL) -> String {
        if let type = UTType(filenameExtension: url.pathExtension) {
            return type.preferredMIMEType ?? "application/octet-stream"
        }
        return "application/octet-stream"
    }
}
