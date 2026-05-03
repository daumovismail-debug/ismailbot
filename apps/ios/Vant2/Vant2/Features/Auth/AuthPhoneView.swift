import SwiftUI

struct AuthPhoneView: View {
    @ObservedObject var session: AppSession

    var body: some View {
        VStack(spacing: 20) {
            Text("Vant2")
                .font(.system(size: 42, weight: .bold, design: .rounded))

            TextField("Phone", text: $session.phone)
                .keyboardType(.phonePad)
                .textFieldStyle(.roundedBorder)

            Button("Отправить OTP") {
                Task { await session.requestOTP() }
            }
            .buttonStyle(VantPrimaryButtonStyle())

            TextField("OTP код", text: $session.otpCode)
                .keyboardType(.numberPad)
                .textFieldStyle(.roundedBorder)

            Button("Подтвердить") {
                Task { await session.verifyOTP() }
            }
            .buttonStyle(VantPrimaryButtonStyle())

            if let error = session.error {
                Text(error).foregroundColor(.red)
            }
        }
        .padding(24)
    }
}
