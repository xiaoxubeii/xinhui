import Foundation
import Dispatch

enum DateFormatters {
    // NOTE:
    // DateFormatter/ISO8601DateFormatter are not guaranteed to be thread-safe. This app formats dates from
    // both UI (main) and background HealthKit queries. To prevent intermittent "today key" corruption that
    // could reset metrics to 0, we:
    // - format YYYY-MM-DD via Calendar components (no formatter shared state)
    // - serialize ISO8601 formatting/parsing through a dedicated queue
    private static let isoQueue = DispatchQueue(label: "xinhui.dateformatters.iso8601")
    private static let iso8601Formatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()
    private static let iso8601LocalFormatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        f.timeZone = .current
        return f
    }()
    private static let iso8601FormatterWithFractionalSeconds: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    /// ISO8601 timestamp string.
    static func iso8601String(from date: Date) -> String {
        isoQueue.sync { iso8601Formatter.string(from: date) }
    }

    /// ISO8601 timestamp string in local timezone (includes offset).
    static func iso8601StringLocal(from date: Date) -> String {
        isoQueue.sync { iso8601LocalFormatter.string(from: date) }
    }

    /// Parse ISO8601 timestamp string (supports fractional seconds).
    static func iso8601Date(from string: String) -> Date? {
        isoQueue.sync {
            iso8601FormatterWithFractionalSeconds.date(from: string) ?? iso8601Formatter.date(from: string)
        }
    }

    /// Date string in "yyyy-MM-dd" for the current timezone.
    static func dateOnlyString(from date: Date, calendar: Calendar = .current) -> String {
        var cal = calendar
        cal.timeZone = .current
        let comps = cal.dateComponents([.year, .month, .day], from: date)
        guard let y = comps.year, let m = comps.month, let d = comps.day else { return "" }
        return String(format: "%04d-%02d-%02d", y, m, d)
    }

    /// Parse "yyyy-MM-dd" into a Date at local start-of-day.
    static func dateOnlyDate(from string: String, calendar: Calendar = .current) -> Date? {
        let parts = string.split(separator: "-")
        guard parts.count == 3,
              let y = Int(parts[0]),
              let m = Int(parts[1]),
              let d = Int(parts[2]) else { return nil }
        var cal = calendar
        cal.timeZone = .current
        var comps = DateComponents()
        comps.year = y
        comps.month = m
        comps.day = d
        return cal.date(from: comps)
    }

    /// 用于 UI 显示的短日期
    static let displayDate: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .none
        f.locale = Locale(identifier: "zh_CN")
        return f
    }()

    /// 用于 UI 显示的日期时间
    static let displayDateTime: DateFormatter = {
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .short
        f.locale = Locale(identifier: "zh_CN")
        return f
    }()
}
