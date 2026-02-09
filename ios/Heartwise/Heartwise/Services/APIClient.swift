import Foundation

/// 基于 URLSession 的网络层，零第三方依赖。
final class APIClient {
    var baseURL: URL

    init(baseURL: URL? = nil) {
        if let baseURL {
            self.baseURL = baseURL
            return
        }
        if let saved = UserDefaults.standard.string(forKey: Constants.serverURLKey),
           let url = URL(string: saved),
           !saved.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            self.baseURL = url
        } else {
            self.baseURL = Constants.defaultBaseURL
        }
    }

    /// 上传健康数据到后端
    func syncHealthData(_ payload: HealthSyncRequest) async throws -> HealthSyncResponse {
        let url = effectiveBaseURL().appendingPathComponent("healthkit/sync")
        let body = try encodeBody(payload)
        let data = try await performJSONRequest(url: url, method: "POST", body: body)
        return try decodeJSON(HealthSyncResponse.self, from: data)
    }

    // MARK: - Diet (Vision + Logging)

    func recognizeFood(_ payload: DietRecognizeRequest) async throws -> DietRecognizeResponse {
        let url = effectiveBaseURL().appendingPathComponent("diet/recognize")
        let body = try encodeBody(payload)
        let data = try await performJSONRequest(url: url, method: "POST", body: body, timeout: 60)
        return try decodeJSON(DietRecognizeResponse.self, from: data)
    }

    func createDietEntry(_ payload: DietCreateEntryRequest) async throws -> DietCreateEntryResponse {
        let url = effectiveBaseURL().appendingPathComponent("diet/entries")
        let body = try encodeBody(payload)
        let data = try await performJSONRequest(url: url, method: "POST", body: body, timeout: 30)
        return try decodeJSON(DietCreateEntryResponse.self, from: data)
    }

    func fetchDietEntries(
        deviceId: String,
        start: String?,
        end: String?,
        limit: Int = 100,
        offset: Int = 0
    ) async throws -> DietEntriesResponse {
        var url = effectiveBaseURL().appendingPathComponent("diet/entries/\(deviceId)")
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        var queryItems: [URLQueryItem] = [
            URLQueryItem(name: "limit", value: String(limit)),
            URLQueryItem(name: "offset", value: String(offset)),
        ]
        if let start { queryItems.append(URLQueryItem(name: "start", value: start)) }
        if let end { queryItems.append(URLQueryItem(name: "end", value: end)) }
        components?.queryItems = queryItems
        if let newURL = components?.url { url = newURL }

        let data = try await performJSONRequest(url: url, method: "GET", body: nil, timeout: 30)
        return try decodeJSON(DietEntriesResponse.self, from: data)
    }

    func fetchDietSummary(deviceId: String, start: String, end: String) async throws -> DietSummaryResponse {
        var url = effectiveBaseURL().appendingPathComponent("diet/summary/\(deviceId)")
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        components?.queryItems = [
            URLQueryItem(name: "start", value: start),
            URLQueryItem(name: "end", value: end),
        ]
        if let newURL = components?.url { url = newURL }
        let data = try await performJSONRequest(url: url, method: "GET", body: nil, timeout: 30)
        return try decodeJSON(DietSummaryResponse.self, from: data)
    }

    // MARK: - Helpers

    private func effectiveBaseURL() -> URL {
        if let saved = UserDefaults.standard.string(forKey: Constants.serverURLKey) {
            let trimmed = saved.trimmingCharacters(in: .whitespacesAndNewlines)
            if let url = URL(string: trimmed), !trimmed.isEmpty {
                return url
            }
        }
        return baseURL
    }

    private func encodeBody<T: Encodable>(_ value: T) throws -> Data {
        do {
            return try JSONEncoder().encode(value)
        } catch {
            throw SyncError.encodingFailed
        }
    }

    private func decodeJSON<T: Decodable>(_ type: T.Type, from data: Data) throws -> T {
        do {
            return try JSONDecoder().decode(type, from: data)
        } catch {
            throw SyncError.decodingFailed
        }
    }

    private func performJSONRequest(
        url: URL,
        method: String,
        body: Data?,
        timeout: TimeInterval = Constants.syncTimeoutInterval
    ) async throws -> Data {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let body {
            if body.count > Constants.maxPayloadBytes {
                throw SyncError.payloadTooLarge(byteCount: body.count)
            }
            request.httpBody = body
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw SyncError.networkError(underlying: error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw SyncError.networkError(underlying: URLError(.badServerResponse))
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw SyncError.serverError(statusCode: httpResponse.statusCode, message: message)
        }

        return data
    }
}
