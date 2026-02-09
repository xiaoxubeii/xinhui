import Foundation

enum SyncError: LocalizedError {
    case healthKitNotAvailable
    case authorizationDenied(dataType: String)
    case queryFailed(underlying: Error)
    case encodingFailed
    case decodingFailed
    case networkError(underlying: Error)
    case serverError(statusCode: Int, message: String)
    case payloadTooLarge(byteCount: Int)

    var errorDescription: String? {
        switch self {
        case .healthKitNotAvailable:
            return "此设备不支持 HealthKit"
        case .authorizationDenied(let dataType):
            return "未授权访问 \(dataType)，请在设置中开启权限"
        case .queryFailed(let underlying):
            return "数据查询失败: \(underlying.localizedDescription)"
        case .encodingFailed:
            return "数据编码失败"
        case .decodingFailed:
            return "数据解析失败"
        case .networkError(let underlying):
            return "网络错误: \(underlying.localizedDescription)"
        case .serverError(let statusCode, let message):
            return "服务器错误 (\(statusCode)): \(message)"
        case .payloadTooLarge(let byteCount):
            let mb = Double(byteCount) / 1_048_576.0
            return String(format: "数据量过大 (%.1f MB)，请缩短日期范围", mb)
        }
    }
}
