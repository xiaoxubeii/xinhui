import Foundation

/// 基于 URLSession 的网络层，零第三方依赖。
final class APIClient {
    private struct LoginRequest: Encodable {
        let email: String
        let password: String
    }

    private struct ApiKeyRequest: Encodable {
        let name: String
    }

    private struct ApiKeyResponse: Decodable {
        let apiKey: String?
        let key: String?
        let token: String?

        enum CodingKeys: String, CodingKey {
            case apiKey = "api_key"
            case key
            case token
        }
    }

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

    // MARK: - Auth / API Keys

    func login(email: String, password: String) async throws {
        let url = effectiveBaseURL().appendingPathComponent("auth/login")
        let payload = LoginRequest(email: email, password: password)
        _ = try await performJSONRequest(url: url, method: "POST", body: try encodeBody(payload), timeout: 30)
    }

    func createApiKey(name: String) async throws -> String {
        let url = effectiveBaseURL().appendingPathComponent("api-keys")
        let payload = ApiKeyRequest(name: name)
        let data = try await performJSONRequest(url: url, method: "POST", body: try encodeBody(payload), timeout: 30)

        if let decoded = try? JSONDecoder().decode(ApiKeyResponse.self, from: data),
           let apiKey = decoded.apiKey ?? decoded.key ?? decoded.token {
            return apiKey
        }

        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let apiKey = json["api_key"] as? String {
                return apiKey
            }
            if let token = json["token"] as? String {
                return token
            }
            if let key = json["key"] as? String {
                return key
            }
        }

        throw SyncError.decodingFailed
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

    // MARK: - Agent

    func askAgent(_ payload: AgentAskRequest) async throws -> AgentAskResponse {
        let url = effectiveBaseURL().appendingPathComponent("agent/ask")
        let body = try encodeBody(payload)
        let data = try await performJSONRequest(url: url, method: "POST", body: body, timeout: 60)
        return try decodeJSON(AgentAskResponse.self, from: data)
    }

    // MARK: - Artifacts

    func uploadArtifact(
        category: ArtifactCategory,
        title: String?,
        attachSessionId: String?,
        fileData: Data,
        filename: String,
        contentType: String
    ) async throws -> ArtifactUploadResponse {
        let url = effectiveBaseURL().appendingPathComponent("artifacts/upload")
        let boundary = "Boundary-\(UUID().uuidString)"

        var body = Data()

        func appendField(name: String, value: String) {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
            body.append("\(value)\r\n".data(using: .utf8)!)
        }

        appendField(name: "category", value: category.rawValue)
        if let title, !title.isEmpty {
            appendField(name: "title", value: title)
        }
        if let attachSessionId, !attachSessionId.isEmpty {
            appendField(name: "attach_session_id", value: attachSessionId)
        }

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(contentType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 60
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.httpBody = body

        let data = try await performRequest(request)
        return try decodeJSON(ArtifactUploadResponse.self, from: data)
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
        applyAuthHeader(&request)
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

    private func performRequest(_ request: URLRequest) async throws -> Data {
        var request = request
        applyAuthHeader(&request)

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

    private func applyAuthHeader(_ request: inout URLRequest) {
        if let apiKey = UserDefaults.standard.string(forKey: Constants.apiKeyKey),
           !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }
    }
}
