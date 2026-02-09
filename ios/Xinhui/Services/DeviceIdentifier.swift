import Foundation

enum DeviceIdentifier {
    /// 获取或生成持久化的设备 UUID。
    static var current: String {
        if let existing = UserDefaults.standard.string(forKey: Constants.deviceIDKey) {
            return existing
        }
        let newID = UUID().uuidString
        UserDefaults.standard.set(newID, forKey: Constants.deviceIDKey)
        return newID
    }
}
