import MDifyCore
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Form {
            Section("Environment") {
                LabeledContent("Status", value: appState.environmentPhase.title)
                switch appState.environmentPhase {
                case .ready(let status), .missingWorker(let status):
                    LabeledContent("Variant", value: status.kind.displayName)
                    LabeledContent("Worker", value: status.executableURL.path)
                    LabeledContent("Executable", value: status.isExecutable ? "Yes" : "No")
                    if status.kind == .ocr {
                        LabeledContent("OCR Models", value: status.modelsPresent ? "Present" : "Missing")
                        LabeledContent("Model Manifest", value: status.modelManifestURL?.path ?? "Missing")
                        LabeledContent("Model Version", value: status.modelManifestVersion ?? "Unknown")
                    }
                default:
                    EmptyView()
                }
            }

            if appState.isOCRVariant {
                Section("OCR") {
                    Picker("Text Language", selection: $appState.ocrLanguageMode) {
                        Text("Automatic").tag(OCRLanguageMode.auto)
                        Text("Cyrillic").tag(OCRLanguageMode.cyrillic)
                        Text("Latin").tag(OCRLanguageMode.latin)
                    }
                    .pickerStyle(.segmented)
                }
            }

            Section("Actions") {
                Button("Recheck Worker") {
                    Task { await appState.bootstrap() }
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
}
