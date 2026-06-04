import MDifyCore
import SwiftUI

struct SidebarQueueView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var conversionService: ConversionService

    var body: some View {
        VStack(spacing: 0) {
            List(selection: $conversionService.selectedID) {
                if conversionService.items.isEmpty {
                    ContentUnavailableView("No Files", systemImage: "doc.badge.plus", description: Text("Drop documents here or use Add Files."))
                        .padding(.vertical, 24)
                } else {
                    ForEach(conversionService.items) { item in
                        SidebarRow(item: item) {
                            conversionService.removeItem(id: item.id)
                        }
                            .tag(item.id)
                    }
                }
            }
            .listStyle(.sidebar)

            Divider()

            VStack(alignment: .leading, spacing: 8) {
                Label(appState.environmentPhase.title, systemImage: environmentIcon)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Text(appState.outputDirectory?.path ?? "No output folder selected")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(2)
                    .truncationMode(.middle)

                if let importSummary = appState.importSummary {
                    Text(importSummary)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
        }
    }

    private var environmentIcon: String {
        switch appState.environmentPhase {
        case .ready: "checkmark.circle"
        case .missingWorker, .failed: "exclamationmark.triangle"
        case .checkingWorker: "gearshape.2"
        case .idle: "circle"
        }
    }
}

private struct SidebarRow: View {
    let item: ConversionItem
    let removeAction: () -> Void
    @EnvironmentObject private var appState: AppState
    @State private var isHovered = false

    var body: some View {
        ZStack(alignment: .topLeading) {
            Label {
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.displayName)
                        .lineLimit(1)
                    Text(item.status.title)
                        .font(.caption)
                        .foregroundStyle(statusColor)
                    if let relativePath = item.folderRelativeDisplayPath {
                        Text(relativePath)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                }
            } icon: {
                Image(systemName: iconName)
                    .foregroundStyle(statusColor)
                    .frame(width: 18)
            }
            .padding(.leading, isHovered ? 20 : 0)
            .animation(.easeOut(duration: 0.12), value: isHovered)

            if isHovered {
                Button(action: removeAction) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 13, weight: .semibold))
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .help("Remove from queue")
                .offset(x: -2, y: -2)
                .transition(.opacity.combined(with: .scale(scale: 0.9)))
            }
        }
        .contentShape(Rectangle())
        .onHover { isHovered = $0 }
        .contextMenu {
            Button {
                appState.revealOutput(for: item)
            } label: {
                Label("Show in Finder", systemImage: "finder")
            }
            .disabled(!appState.canRevealOutput(for: item))

            Button {
                appState.openOutputFolder(for: item)
            } label: {
                Label("Open Output Folder", systemImage: "folder")
            }
            .disabled(!appState.canRevealOutput(for: item))

            Divider()

            Button {
                appState.copyMarkdown(for: item)
            } label: {
                Label("Copy Markdown", systemImage: "doc.on.doc")
            }
            .disabled(item.markdownText.isEmpty)

            Divider()

            Button(role: .destructive, action: removeAction) {
                Label("Remove from Queue", systemImage: "xmark.circle")
            }
        }
        .help(item.inputURL.path)
    }

    private var iconName: String {
        switch item.status {
        case .pending: "doc"
        case .converting: "arrow.triangle.2.circlepath"
        case .succeeded: "checkmark.circle"
        case .failed: "xmark.octagon"
        case .cancelled: "stop.circle"
        }
    }

    private var statusColor: Color {
        switch item.status {
        case .pending: .secondary
        case .converting: .blue
        case .succeeded: .green
        case .failed: .red
        case .cancelled: .orange
        }
    }
}
