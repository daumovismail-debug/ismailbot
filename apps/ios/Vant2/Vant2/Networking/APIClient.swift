import Foundation

struct APIClient {
    var baseURL: URL = URL(string: "http://localhost:8080")!

    func sendOTP(phone: String) async throws {
        var req = URLRequest(url: baseURL.appendingPathComponent("/v1/auth/send-otp"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["phone": phone])
        _ = try await URLSession.shared.data(for: req)
    }

    func verifyOTP(phone: String, code: String) async throws -> String {
        var req = URLRequest(url: baseURL.appendingPathComponent("/v1/auth/verify-otp"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(["phone": phone, "code": code])
        let (data, _) = try await URLSession.shared.data(for: req)
        let value = try JSONDecoder().decode(TokenResponse.self, from: data)
        return value.token
    }

    func fetchChats(token: String) async throws -> [ChatDTO] {
        var req = URLRequest(url: baseURL.appendingPathComponent("/v1/chats"))
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (data, _) = try await URLSession.shared.data(for: req)
        return try JSONDecoder().decode([ChatDTO].self, from: data)
    }
}

struct TokenResponse: Decodable { let token: String }
struct ChatDTO: Decodable, Identifiable { let id: String; let title: String }
