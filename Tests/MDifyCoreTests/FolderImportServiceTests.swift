import XCTest
@testable import MDifyCore

final class FolderImportServiceTests: XCTestCase {
    func testTopLevelScanSkipsUnsupportedHiddenSymlinksPackagesAndSubfolders() throws {
        let root = try makeFolderFixture()

        let result = try FolderImportService().scan(root: root, mode: .topLevelOnly)

        XCTAssertEqual(result.files.map(\.url.lastPathComponent).sorted(), ["report.pdf"])
        XCTAssertEqual(result.skippedUnsupportedCount, 3)
        XCTAssertTrue(result.hasSubfolders)
    }

    func testRecursiveScanIncludesSupportedFilesInSubfolders() throws {
        let root = try makeFolderFixture()

        let result = try FolderImportService().scan(root: root, mode: .recursive)

        XCTAssertEqual(result.files.map(\.relativePath).sorted(), ["nested/notes.txt", "report.pdf"])
        XCTAssertEqual(result.skippedUnsupportedCount, 3)
        XCTAssertTrue(result.hasSubfolders)
    }

    private func makeFolderFixture() throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let nested = root.appendingPathComponent("nested", isDirectory: true)
        let package = root.appendingPathComponent("Preview.app", isDirectory: true)
        try FileManager.default.createDirectory(at: nested, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: package, withIntermediateDirectories: true)

        try Data().write(to: root.appendingPathComponent("report.pdf"))
        try Data().write(to: root.appendingPathComponent("todo.exe"))
        try Data().write(to: root.appendingPathComponent(".hidden.pdf"))
        try Data().write(to: root.appendingPathComponent(".DS_Store"))
        try Data().write(to: nested.appendingPathComponent("notes.txt"))
        try Data().write(to: package.appendingPathComponent("inside.pdf"))

        let symlink = root.appendingPathComponent("linked.txt")
        try FileManager.default.createSymbolicLink(at: symlink, withDestinationURL: nested.appendingPathComponent("notes.txt"))

        addTeardownBlock {
            try? FileManager.default.removeItem(at: root)
        }
        return root
    }
}
