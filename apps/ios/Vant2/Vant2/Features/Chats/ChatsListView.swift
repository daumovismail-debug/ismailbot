import SwiftUI

struct ChatsListView: View {
    @ObservedObject var session: AppSession
    @State private var chats: [ChatDTO] = []

    var body: some View {
        NavigationStack {
            List(chats) { chat in
                NavigationLink(destination: ChatDetailView(title: chat.title)) {
                    Text(chat.title)
                }
            }
            .navigationTitle("Vant2")
            .task {
                do {
                    chats = try await session.api.fetchChats(token: session.token)
                } catch {
                    session.error = "Не удалось загрузить чаты"
                }
            }
        }
    }
}
