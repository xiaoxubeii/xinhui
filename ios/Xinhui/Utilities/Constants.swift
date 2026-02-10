import Foundation
import CoreGraphics

enum Constants {
    static let defaultBaseURL = URL(string: "http://58.222.210.226:8000/api")!
    static let syncTimeoutInterval: TimeInterval = 60
    static let maxPayloadBytes = 5 * 1024 * 1024 // 5 MB
    static let defaultSyncDays = 30
    static let autoSyncDays = 7
    static let autoSyncMinInterval: TimeInterval = 6 * 3600
    static let cornerRadius: CGFloat = 12

    static let serverURLKey = "xinhui_server_url"
    static let lastSyncDateKey = "xinhui_last_sync"
    static let deviceIDKey = "xinhui_device_id"
    static let apiKeyKey = "xinhui_api_key"
    static let autoSyncEnabledKey = "xinhui_auto_sync_enabled"
    static let lastAutoSyncAttemptDateKey = "xinhui_last_auto_sync_attempt"
    static let lastAutoSyncSuccessDateKey = "xinhui_last_auto_sync_success"
    static let lastAutoSyncErrorKey = "xinhui_last_auto_sync_error"

}
