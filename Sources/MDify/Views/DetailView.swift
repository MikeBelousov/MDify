import MDifyCore
import SwiftUI

struct DetailView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var conversionService: ConversionService

    var body: some View {
        Group {
            switch appState.environmentPhase {
            case .missingWorker(let status):
                SetupView(
                    title: "Embedded Worker Missing",
                    message: missingWorkerMessage(status),
                    primaryTitle: "Recheck",
                    primaryAction: { Task { await appState.bootstrap() } }
                )
            case .failed(let message):
                SetupView(
                    title: "Setup Failed",
                    message: message,
                    primaryTitle: "Recheck",
                    primaryAction: { Task { await appState.bootstrap() } }
                )
            case .checkingWorker:
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

    private func missingWorkerMessage(_ status: WorkerBundleStatus) -> String {
        if !status.isExecutable {
            return "The \(status.kind.displayName) worker is not bundled at \(status.executableURL.path). Rebuild the app bundle."
        }
        if status.kind == .ocr && !status.modelsPresent {
            return "The \(status.kind.displayName) worker is bundled, but OCR models are missing. Rebuild the OCR bundle with the model manifest."
        }
        return "The embedded worker bundle is incomplete. Rebuild the app bundle."
    }
}
