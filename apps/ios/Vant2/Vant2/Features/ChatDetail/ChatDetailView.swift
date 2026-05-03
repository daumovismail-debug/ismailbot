import SwiftUI

struct Message: Identifiable {
    let id = UUID()
    let text: String
    let isOutgoing: Bool
}

struct ChatDetailView: View {
    let title: String
    @State private var draft = ""
    @State private var messages: [Message] = [
        Message(text: "Привет 👋", isOutgoing: false),
        Message(text: "Готовим Vant2", isOutgoing: true)
    ]

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 10) {
                    ForEach(messages) { msg in
                        HStack {
                            if msg.isOutgoing { Spacer() }
                            Text(msg.text)
                                .padding(10)
                                .background(msg.isOutgoing ? Color.blue : Color.gray.opacity(0.2))
                                .foregroundStyle(msg.isOutgoing ? Color.white : Color.primary)
                                .clipShape(RoundedRectangle(cornerRadius: 14))
                            if !msg.isOutgoing { Spacer() }
                        }
                        .transition(.asymmetric(insertion: .scale(scale: 0.98).combined(with: .opacity), removal: .opacity))
                    }
                }
                .padding()
            }

            HStack {
                TextField("Сообщение", text: $draft)
                    .textFieldStyle(.roundedBorder)
                Button("Send") {
                    guard !draft.isEmpty else { return }
                    withAnimation(.easeOut(duration: 0.16)) {
                        messages.append(Message(text: draft, isOutgoing: true))
                        draft = ""
                    }
                }
            }
            .padding()
            .background(.ultraThinMaterial)
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
