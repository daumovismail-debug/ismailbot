import SwiftUI

struct RootView: View {
    @StateObject private var session = AppSession()

    var body: some View {
        Group {
            if session.isAuthenticated {
                ChatsListView(session: session)
            } else {
                AuthPhoneView(session: session)
            }
        }
        .animation(.spring(response: 0.38, dampingFraction: 0.82), value: session.isAuthenticated)
    }
}
