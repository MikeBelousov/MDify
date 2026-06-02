import MDifyCore
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Form {
            Section("Environment") {
                LabeledContent("Status", value: appState.environmentPhase.title)
                LabeledContent("MarkItDown", value: appState.markitdownExecutableURL.path)
                if case .ready(let python, let state) = appState.environmentPhase {
                    LabeledContent("Python", value: python.executableURL.path)
                    LabeledContent("Python Version", value: python.version.description)
                    LabeledContent("Architecture", value: python.architecture.rawValue)
                    LabeledContent("Library", value: libraryDescription(state))
                }
            }

            Section("Actions") {
                Button("Recheck Environment") {
                    Task { await appState.bootstrap() }
                }
                Button("Download Python") {
                    appState.openPythonDownload()
                }
            }

            Section("Setup Log") {
                TextEditor(text: .constant(appState.setupLog.isEmpty ? "No setup log yet." : appState.setupLog))
                    .font(.system(.caption, design: .monospaced))
                    .frame(minHeight: 120)
            }
        }
        .padding()
    }

    private func libraryDescription(_ state: MarkItDownInstallState) -> String {
        switch state {
        case .missing: "Missing"
        case .installed(let version): "Installed \(version)"
        case .wrongVersion(let version): "Wrong version \(version)"
        }
    }
}
