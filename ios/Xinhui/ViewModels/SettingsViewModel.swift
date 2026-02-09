import Foundation
import Combine
import HealthKit

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var serverURL: String = ""
    @Published var deviceId: String = ""
    @Published var healthKitAvailable: Bool = false
    @Published var permissionStatuses: [(name: String, granted: Bool)] = []
    @Published var autoSyncEnabled: Bool = false
    @Published var lastAutoSyncAttemptDate: Date?
    @Published var lastAutoSyncSuccessDate: Date?
    @Published var lastAutoSyncError: String = ""
    @Published var loginEmail: String = ""
    @Published var loginPassword: String = ""
    @Published var apiKey: String = ""
    @Published var authStatus: String = ""
    @Published var authError: String = ""
    @Published var isAuthBusy: Bool = false

    func load() {
        deviceId = DeviceIdentifier.current
        healthKitAvailable = HKHealthStore.isHealthDataAvailable()

        if let saved = UserDefaults.standard.string(forKey: Constants.serverURLKey), !saved.isEmpty {
            serverURL = saved
        } else {
            serverURL = Constants.defaultBaseURL.absoluteString
        }

        refreshAutoSyncStatus()
        refreshApiKeyStatus()
        refreshPermissions()
    }

    func saveServerURL() {
        let trimmed = serverURL.trimmingCharacters(in: .whitespacesAndNewlines)
        UserDefaults.standard.set(trimmed, forKey: Constants.serverURLKey)
    }

    func saveAutoSyncEnabled() {
        UserDefaults.standard.set(autoSyncEnabled, forKey: Constants.autoSyncEnabledKey)
    }

    func refreshApiKeyStatus() {
        apiKey = UserDefaults.standard.string(forKey: Constants.apiKeyKey) ?? ""
    }

    func clearApiKey() {
        UserDefaults.standard.removeObject(forKey: Constants.apiKeyKey)
        refreshApiKeyStatus()
        authStatus = "已清除 API Key"
    }

    func loginAndCreateApiKey() async {
        guard !isAuthBusy else { return }
        let email = loginEmail.trimmingCharacters(in: .whitespacesAndNewlines)
        let password = loginPassword
        let server = serverURL.trimmingCharacters(in: .whitespacesAndNewlines)

        authError = ""
        authStatus = ""

        guard !email.isEmpty, !password.isEmpty else {
            authError = "请输入邮箱和密码"
            return
        }

        guard let baseURL = URL(string: server), !server.isEmpty else {
            authError = "服务器地址无效，请先设置并保存"
            return
        }

        isAuthBusy = true
        defer { isAuthBusy = false }

        do {
            UserDefaults.standard.set(server, forKey: Constants.serverURLKey)
            let api = APIClient(baseURL: baseURL)
            try await api.login(email: email, password: password)
            let key = try await api.createApiKey(name: "ios")
            UserDefaults.standard.set(key, forKey: Constants.apiKeyKey)
            refreshApiKeyStatus()
            loginPassword = ""
            authStatus = "已创建 API Key"
        } catch {
            authError = error.localizedDescription
        }
    }

    func refreshAutoSyncStatus() {
        autoSyncEnabled = UserDefaults.standard.bool(forKey: Constants.autoSyncEnabledKey)
        lastAutoSyncAttemptDate = UserDefaults.standard.object(forKey: Constants.lastAutoSyncAttemptDateKey) as? Date
        lastAutoSyncSuccessDate = UserDefaults.standard.object(forKey: Constants.lastAutoSyncSuccessDateKey) as? Date
        lastAutoSyncError = UserDefaults.standard.string(forKey: Constants.lastAutoSyncErrorKey) ?? ""
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

    var lastAutoSyncAttemptText: String {
        if let lastAutoSyncAttemptDate {
            return DateFormatters.displayDateTime.string(from: lastAutoSyncAttemptDate)
        }
        return "--"
    }

    var lastAutoSyncSuccessText: String {
        if let lastAutoSyncSuccessDate {
            return DateFormatters.displayDateTime.string(from: lastAutoSyncSuccessDate)
        }
        return "--"
    }

    var apiKeyMasked: String {
        if apiKey.isEmpty { return "--" }
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.count <= 12 { return trimmed }
        let prefix = trimmed.prefix(8)
        let suffix = trimmed.suffix(4)
        return "\(prefix)...\(suffix)"
    }
}
