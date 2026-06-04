import Combine
import Foundation

@MainActor
public final class ConversionService: ObservableObject {
    @Published public private(set) var items: [ConversionItem] = []
    @Published public var selectedID: UUID?
    @Published public private(set) var isConverting = false

    private let workerClient: any WorkerConverting
    private let namer: OutputFileNamer
    private var shouldCancel = false

    public init(
        workerClient: any WorkerConverting = WorkerBundleResolver().makeNativeRoutingClient(),
        namer: OutputFileNamer = OutputFileNamer()
    ) {
        self.workerClient = workerClient
        self.namer = namer
    }

    public var selectedItem: ConversionItem? {
        guard let selectedID else { return items.first }
        return items.first(where: { $0.id == selectedID })
    }

    public func enqueue(files: [URL]) {
        let existing = Set(items.map(\.inputURL))
        let newItems = files
            .filter { $0.isFileURL && !existing.contains($0) }
            .map { ConversionItem(inputURL: $0) }
        items.append(contentsOf: newItems)
        if selectedID == nil {
            selectedID = items.first?.id
        }
    }

    @discardableResult
    public func enqueue(folderScan: FolderScanResult) -> FolderImportSummary {
        let existing = Set(items.map(\.inputURL))
        let scannedFiles = folderScan.files.filter { !existing.contains($0.url) }
        let newItems = scannedFiles.map {
            ConversionItem(
                inputURL: $0.url,
                sourceRootURL: folderScan.rootURL,
                relativeOutputPath: $0.relativePath
            )
        }
        items.append(contentsOf: newItems)
        if selectedID == nil {
            selectedID = items.first?.id
        }

        return FolderImportSummary(
            addedCount: newItems.count,
            skippedUnsupportedCount: folderScan.skippedUnsupportedCount,
            skippedDuplicateCount: folderScan.files.count - scannedFiles.count
        )
    }

    public func clearCompleted() {
        items.removeAll { $0.status == .succeeded || $0.status == .failed || $0.status == .cancelled }
        if let selectedID, !items.contains(where: { $0.id == selectedID }) {
            self.selectedID = items.first?.id
        }
    }

    public func removeItem(id: UUID) {
        items.removeAll { $0.id == id }
        if selectedID == id || selectedID == nil || !items.contains(where: { $0.id == selectedID }) {
            selectedID = items.first?.id
        }
    }

    public func cancel() {
        shouldCancel = true
    }

    public func convertAll(outputDirectory: URL) async {
        guard !isConverting else { return }
        isConverting = true
        shouldCancel = false
        defer { isConverting = false }

        var reservedNames = Set<String>()
        var reservedRoots: [String: URL] = [:]
        for item in items where item.status == .pending || item.status == .failed {
            if shouldCancel {
                update(item.id) { $0.status = .cancelled }
                continue
            }

            let outputURL: URL
            if item.sourceRootURL == nil {
                outputURL = namer.markdownURL(for: item.inputURL, in: outputDirectory, reserved: reservedNames)
                reservedNames.insert(outputURL.lastPathComponent)
            } else {
                outputURL = namer.markdownURL(for: item, in: outputDirectory, reservedRoots: &reservedRoots)
            }
            await convert(itemID: item.id, outputURL: outputURL)
        }
    }

    private func convert(itemID: UUID, outputURL: URL) async {
        guard let item = items.first(where: { $0.id == itemID }) else { return }
        update(itemID) {
            $0.status = .converting
            $0.errorMessage = nil
            $0.outputURL = outputURL
            $0.log = "Running embedded MDify worker for \(item.inputURL.path)"
        }

        do {
            let response = try await workerClient.convert(inputURL: item.inputURL, outputURL: outputURL)
            guard response.ok else {
                update(itemID) {
                    $0.status = .failed
                    $0.errorMessage = response.message ?? response.errorCode ?? "Conversion failed."
                    $0.log = response.errorCode ?? "Worker reported failure."
                }
                return
            }

            let markdown = try String(contentsOf: outputURL, encoding: .utf8)
            update(itemID) {
                $0.status = .succeeded
                $0.markdownText = markdown
                $0.outputURL = outputURL
                $0.log = workerLog(response)
            }
        } catch {
            update(itemID) {
                $0.status = .failed
                $0.errorMessage = error.localizedDescription
                $0.log = error.localizedDescription
            }
        }
    }

    private func workerLog(_ response: WorkerResponse) -> String {
        var lines = [
            "Worker: \(response.worker)",
            "Engine: \(response.engine ?? "unknown")",
            "OCR used: \(response.ocrUsed ? "yes" : "no")"
        ]
        if !response.warnings.isEmpty {
            lines.append("Warnings: \(response.warnings.joined(separator: "; "))")
        }
        return lines.joined(separator: "\n")
    }

    private func update(_ id: UUID, mutate: (inout ConversionItem) -> Void) {
        guard let index = items.firstIndex(where: { $0.id == id }) else { return }
        mutate(&items[index])
    }
}
