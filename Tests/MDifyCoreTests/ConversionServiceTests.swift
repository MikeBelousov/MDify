import XCTest
@testable import MDifyCore

@MainActor
final class ConversionServiceTests: XCTestCase {
    func testQueueConvertsSuccessfulFileAndWritesMarkdown() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let inputURL = directory.appendingPathComponent("sample.txt")
        try "hello".write(to: inputURL, atomically: true, encoding: .utf8)

        let service = ConversionService(
            workerClient: MockWorkerClient(behaviors: [
                "sample.txt": .success("# Hello\n")
            ])
        )

        service.enqueue(files: [inputURL])
        await service.convertAll(outputDirectory: directory)

        XCTAssertEqual(service.items.first?.status, .succeeded)
        XCTAssertEqual(service.items.first?.markdownText, "# Hello\n")
        XCTAssertEqual(
            try String(contentsOf: directory.appendingPathComponent("sample.md"), encoding: .utf8),
            "# Hello\n"
        )
    }

    func testQueueStoresFailureMessage() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let inputURL = directory.appendingPathComponent("broken.pdf")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())

        let service = ConversionService(
            workerClient: MockWorkerClient(behaviors: [
                "broken.pdf": .failure("cannot parse", code: "CONVERSION_FAILED")
            ])
        )

        service.enqueue(files: [inputURL])
        await service.convertAll(outputDirectory: directory)

        XCTAssertEqual(service.items.first?.status, .failed)
        XCTAssertEqual(service.items.first?.errorMessage, "cannot parse")
    }

    func testRemoveQueuedFileUpdatesSelection() {
        let service = ConversionService()
        let first = URL(fileURLWithPath: "/tmp/first.pdf")
        let second = URL(fileURLWithPath: "/tmp/second.docx")

        service.enqueue(files: [first, second])
        XCTAssertEqual(service.selectedItem?.inputURL, first)

        service.removeItem(id: service.items[0].id)

        XCTAssertEqual(service.items.map(\.inputURL), [second])
        XCTAssertEqual(service.selectedItem?.inputURL, second)

        service.removeItem(id: service.items[0].id)

        XCTAssertTrue(service.items.isEmpty)
        XCTAssertNil(service.selectedID)
    }

    func testEnqueueFolderScanSkipsDuplicatesAndKeepsRelativeOutputMetadata() {
        let service = ConversionService()
        let root = URL(fileURLWithPath: "/tmp/Source")
        let first = root.appendingPathComponent("report.pdf")
        let nested = root.appendingPathComponent("nested/notes.txt")
        let scan = FolderScanResult(
            rootURL: root,
            files: [
                FolderScannedFile(url: first, relativePath: "report.pdf"),
                FolderScannedFile(url: nested, relativePath: "nested/notes.txt")
            ],
            skippedUnsupportedCount: 3,
            hasSubfolders: true
        )

        service.enqueue(files: [first])
        let summary = service.enqueue(folderScan: scan)

        XCTAssertEqual(summary.addedCount, 1)
        XCTAssertEqual(summary.skippedUnsupportedCount, 3)
        XCTAssertEqual(service.items.count, 2)
        XCTAssertEqual(service.items[1].sourceRootURL, root)
        XCTAssertEqual(service.items[1].relativeOutputPath, "nested/notes.txt")
    }

    func testFolderConversionWritesMirroredOutputTree() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let root = directory.appendingPathComponent("Source")
        let nested = root.appendingPathComponent("nested")
        let outputDirectory = directory.appendingPathComponent("Output")
        try FileManager.default.createDirectory(at: nested, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: outputDirectory, withIntermediateDirectories: true)
        let inputURL = nested.appendingPathComponent("notes.txt")
        try "hello".write(to: inputURL, atomically: true, encoding: .utf8)

        let service = ConversionService(
            workerClient: MockWorkerClient(behaviors: [
                "notes.txt": .success("# Notes\n")
            ])
        )
        _ = service.enqueue(folderScan: FolderScanResult(
            rootURL: root,
            files: [FolderScannedFile(url: inputURL, relativePath: "nested/notes.txt")],
            skippedUnsupportedCount: 0,
            hasSubfolders: true
        ))

        await service.convertAll(outputDirectory: outputDirectory)

        let outputURL = outputDirectory.appendingPathComponent("Source/nested/notes.md")
        XCTAssertEqual(try String(contentsOf: outputURL, encoding: .utf8), "# Notes\n")
        XCTAssertEqual(service.items.first?.outputURL, outputURL)
    }
}
