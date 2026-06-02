import MDifyCore
import SwiftUI

struct MarkdownPreviewView: View {
    enum Mode: String, CaseIterable, Identifiable {
        case preview = "Preview"
        case raw = "Raw"
        case log = "Log"

        var id: String { rawValue }
    }

    let item: ConversionItem
    @EnvironmentObject private var appState: AppState
    @State private var mode: Mode = .preview

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            content
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(item.displayName)
                    .font(.headline)
                    .lineLimit(1)
                HStack(spacing: 6) {
                    Text(item.outputURL?.path ?? item.inputURL.path)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)

                    if appState.canRevealOutput(for: item) {
                        Button {
                            appState.revealOutput(for: item)
                        } label: {
                            Label("Show in Finder", systemImage: "finder")
                                .labelStyle(.iconOnly)
                        }
                        .buttonStyle(.borderless)
                        .help("Show in Finder")

                        Button {
                            appState.openOutputFolder(for: item)
                        } label: {
                            Label("Open Output Folder", systemImage: "folder")
                                .labelStyle(.iconOnly)
                        }
                        .buttonStyle(.borderless)
                        .help("Open Output Folder")
                    }
                }
            }
            Spacer()
            Picker("Mode", selection: $mode) {
                ForEach(Mode.allCases) { mode in
                    Text(mode.rawValue).tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .frame(width: 240)
        }
        .padding()
    }

    @ViewBuilder
    private var content: some View {
        switch mode {
        case .preview:
            ScrollView {
                Text(renderedMarkdown)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
                    .padding(24)
            }
        case .raw:
            TextEditor(text: .constant(item.markdownText))
                .font(.system(.body, design: .monospaced))
                .padding(8)
        case .log:
            TextEditor(text: .constant(logText))
                .font(.system(.body, design: .monospaced))
                .padding(8)
        }
    }

    private var renderedMarkdown: AttributedString {
        if item.markdownText.isEmpty {
            return AttributedString(item.errorMessage ?? "Convert this file to see Markdown here.")
        }
        return (try? AttributedString(markdown: item.markdownText)) ?? AttributedString(item.markdownText)
    }

    private var logText: String {
        if let error = item.errorMessage, !error.isEmpty {
            return "\(error)\n\n\(item.log)"
        }
        return item.log.isEmpty ? "No log output." : item.log
    }
}
