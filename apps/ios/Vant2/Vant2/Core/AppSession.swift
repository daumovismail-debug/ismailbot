import Foundation
import SwiftUI

@MainActor
final class AppSession: ObservableObject {
    @Published var token: String = ""
    @Published var phone: String = ""
    @Published var otpCode: String = ""
    @Published var error: String?

    let api = APIClient()

    var isAuthenticated: Bool { !token.isEmpty }

    func requestOTP() async {
        do {
            try await api.sendOTP(phone: phone)
            error = nil
        } catch {
            self.error = "Не удалось отправить OTP"
        }
    }

    func verifyOTP() async {
        do {
            token = try await api.verifyOTP(phone: phone, code: otpCode)
            error = nil
        } catch {
            self.error = "Неверный код или ошибка сети"
        }
    }
}
