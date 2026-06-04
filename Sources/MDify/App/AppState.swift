import AppKit
import Combine
import Foundation
import MDifyCore

@MainActor
final class AppState: ObservableObject {
    enum EnvironmentPhase: Equatable {
        case idle
        case checkingWorker
        case ready(WorkerBundleStatus)
        case missingWorker(WorkerBundleStatus)
        case failed(String)

        var title: String {
            switch self {
            case .idle: "Not checked"
            case .checkingWorker: "Checking Worker"
            case .ready: "Ready"
            case .missingWorker: "Worker missing"
            case .failed: "Setup failed"
            }
        }
    }

    @Published var environmentPhase: EnvironmentPhase = .idle
    @Published var outputDirectory: URL? = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first
    @Published var setupLog = ""
    @Published var importSummary: String?

    let conversionService: ConversionService
    private let folderImportService: FolderImportService
    private let outputRevealPolicy = OutputRevealPolicy()
    private let workerResolver: WorkerBundleResolver

    init(workerResolver: WorkerBundleResolver = WorkerBundleResolver()) {
        self.workerResolver = workerResolver
        self.conversionService = ConversionService(workerClient: workerResolver.makeNativeRoutingClient())
        self.folderImportService = FolderImportService(
            policy: ConvertibleFilePolicy(workerKind: workerResolver.workerKind)
        )
    }

    func bootstrapIfNeeded() async {
        if case .ready = environmentPhase { return }
        await bootstrap()
    }

    func bootstrap() async {
        environmentPhase = .checkingWorker
        setupLog = ""

        let status = workerResolver.status()
        setupLog = setupDescription(for: status)
        if status.isExecutable && status.modelsPresent {
            environmentPhase = .ready(status)
        } else {
            environmentPhase = .missingWorker(status)
        }
    }

    func enqueue(_ urls: [URL]) {
        conversionService.enqueue(files: urls)
    }

    func importURLs(_ urls: [URL]) {
        var fileURLs: [URL] = []
        for url in urls where url.isFileURL {
            if isDirectory(url) {
                importFolder(url)
            } else {
                fileURLs.append(url)
            }
        }

        if !fileURLs.isEmpty {
            let before = conversionService.items.count
            conversionService.enqueue(files: fileURLs)
            let added = conversionService.items.count - before
            importSummary = "Added \(added) files"
        }
    }

    func chooseFiles() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        if panel.runModal() == .OK {
            importURLs(panel.urls)
        }
    }

    func chooseFolder() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let folderURL = panel.url {
            importFolder(folderURL)
        }
    }

    func chooseOutputDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK {
            outputDirectory = panel.url
        }
    }

    func convertAll() async {
        guard let outputDirectory else {
            chooseOutputDirectory()
            guard self.outputDirectory != nil else { return }
            await convertAll()
            return
        }
        await bootstrapIfNeeded()
        guard case .ready = environmentPhase else { return }
        await conversionService.convertAll(outputDirectory: outputDirectory)
    }

    func copySelectedMarkdown() {
        guard let item = conversionService.selectedItem else { return }
        copyMarkdown(for: item)
    }

    func copyMarkdown(for item: ConversionItem) {
        guard !item.markdownText.isEmpty else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(item.markdownText, forType: .string)
    }

    func canRevealOutput(for item: ConversionItem?) -> Bool {
        guard let item else { return false }
        return outputRevealPolicy.canRevealOutput(for: item)
    }

    func revealOutput(for item: ConversionItem) {
        guard canRevealOutput(for: item), let outputURL = item.outputURL else { return }
        NSWorkspace.shared.activateFileViewerSelecting([outputURL])
    }

    func revealSelectedOutput() {
        guard let item = conversionService.selectedItem else { return }
        revealOutput(for: item)
    }

    func openOutputFolder(for item: ConversionItem) {
        guard canRevealOutput(for: item), let outputURL = item.outputURL else { return }
        NSWorkspace.shared.open(outputURL.deletingLastPathComponent())
    }

    private func importFolder(_ folderURL: URL) {
        do {
            let topLevelScan = try folderImportService.scan(root: folderURL, mode: .topLevelOnly)
            guard topLevelScan.hasSubfolders else {
                applyFolderScan(topLevelScan)
                return
            }

            switch askFolderScanMode(folderName: folderURL.lastPathComponent) {
            case .recursive:
                applyFolderScan(try folderImportService.scan(root: folderURL, mode: .recursive))
            case .topLevelOnly:
                applyFolderScan(topLevelScan)
            case .cancelled:
                break
            }
        } catch {
            importSummary = "Could not scan folder: \(error.localizedDescription)"
        }
    }

    private func applyFolderScan(_ scan: FolderScanResult) {
        let summary = conversionService.enqueue(folderScan: scan)
        importSummary = summary.displayText
    }

    private enum FolderScanChoice {
        case recursive
        case topLevelOnly
        case cancelled
    }

    private func askFolderScanMode(folderName: String) -> FolderScanChoice {
        let alert = NSAlert()
        alert.messageText = "Add files from subfolders?"
        alert.informativeText = "\"\(folderName)\" contains subfolders. Include supported files inside them too?"
        alert.addButton(withTitle: "Include Subfolders")
        alert.addButton(withTitle: "Top Level Only")
        alert.addButton(withTitle: "Cancel")

        switch alert.runModal() {
        case .alertFirstButtonReturn:
            return .recursive
        case .alertSecondButtonReturn:
            return .topLevelOnly
        default:
            return .cancelled
        }
    }

    private func isDirectory(_ url: URL) -> Bool {
        var isDirectory: ObjCBool = false
        return FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory) && isDirectory.boolValue
    }

    private func setupDescription(for status: WorkerBundleStatus) -> String {
        var lines = [
            "Worker kind: \(status.kind.rawValue)",
            "Worker path: \(status.executableURL.path)",
            "Worker executable: \(status.isExecutable ? "yes" : "no")"
        ]
        if status.kind == .ocr {
            lines.append("OCR models: \(status.modelsPresent ? "present" : "missing")")
            lines.append("OCR model manifest: \(status.modelManifestURL?.path ?? "missing")")
            if let version = status.modelManifestVersion {
                lines.append("OCR model version: \(version)")
            }
        }
        return lines.joined(separator: "\n")
    }
}
