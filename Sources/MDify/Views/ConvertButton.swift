import SwiftUI

struct ConvertButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label("Convert", systemImage: "number")
                .labelStyle(.titleAndIcon)
        }
        .buttonStyle(.borderedProminent)
        .tint(Self.brandBackground)
        .help("Convert to Markdown")
        .accessibilityLabel("Convert to Markdown")
    }

    private static let brandBackground = Color(red: 17 / 255, green: 24 / 255, blue: 39 / 255)
}
