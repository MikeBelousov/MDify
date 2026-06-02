import Combine
import Foundation

@MainActor
public final class ConversionService: ObservableObject {
    @Published public private(set) var items: [ConversionItem] = []
    @Published public var selectedID: UUID?
    @Published public private(set) var isConverting = false

    private let runner: any ProcessRunning
    private let namer: OutputFileNamer
    private var shouldCancel = false

    public init(
        runner: any ProcessRunning = ProcessRunner(),
        namer: OutputFileNamer = OutputFileNamer()
    ) {
        self.runner = runner
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

    public func convertAll(outputDirectory: URL, markitdownExecutable: URL) async {
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
            await convert(itemID: item.id, outputURL: outputURL, markitdownExecutable: markitdownExecutable)
        }
    }

    private func convert(itemID: UUID, outputURL: URL, markitdownExecutable: URL) async {
        guard let item = items.first(where: { $0.id == itemID }) else { return }
        update(itemID) {
            $0.status = .converting
            $0.errorMessage = nil
            $0.outputURL = outputURL
            $0.log = "Running MarkItDown for \(item.inputURL.path)"
        }

        do {
            let result = try await runner.run(
                executableURL: markitdownExecutable,
                arguments: [item.inputURL.path],
                environment: nil
            )
            guard result.exitCode == 0 else {
                update(itemID) {
                    $0.status = .failed
                    $0.errorMessage = result.stderr.isEmpty ? "MarkItDown exited with code \(result.exitCode)." : result.stderr
                    $0.log = result.stdout + result.stderr
                }
                return
            }

            try FileManager.default.createDirectory(
                at: outputURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try result.stdout.write(to: outputURL, atomically: true, encoding: .utf8)
            update(itemID) {
                $0.status = .succeeded
                $0.markdownText = result.stdout
                $0.outputURL = outputURL
                $0.log = result.stderr
            }
        } catch {
            update(itemID) {
                $0.status = .failed
                $0.errorMessage = error.localizedDescription
                $0.log = error.localizedDescription
            }
        }
    }

    private func update(_ id: UUID, mutate: (inout ConversionItem) -> Void) {
        guard let index = items.firstIndex(where: { $0.id == id }) else { return }
        mutate(&items[index])
    }
}
