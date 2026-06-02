import MDifyCore
import SwiftUI

struct DetailView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var conversionService: ConversionService

    var body: some View {
        Group {
            switch appState.environmentPhase {
            case .missingPython:
                SetupView(
                    title: "Python 3.10+ Required",
                    message: "MDify installs MarkItDown automatically, but it needs a compatible Python first.",
                    primaryTitle: "Download Python",
                    primaryAction: appState.openPythonDownload,
                    secondaryTitle: "Recheck",
                    secondaryAction: { Task { await appState.bootstrap() } }
                )
            case .failed(let message):
                SetupView(
                    title: "Setup Failed",
                    message: message,
                    primaryTitle: "Recheck",
                    primaryAction: { Task { await appState.bootstrap() } },
                    secondaryTitle: "Download Python",
                    secondaryAction: appState.openPythonDownload
                )
            case .checking, .installing:
                ProgressView(appState.environmentPhase.title)
                    .controlSize(.large)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            case .idle, .ready:
                if let item = conversionService.selectedItem {
                    MarkdownPreviewView(item: item)
                } else {
                    DropZoneView()
                }
            }
        }
    }
}
