import XCTest
@testable import MDifyCore

final class OutputFileNamerTests: XCTestCase {
    func testCreatesMarkdownNameFromOriginalFileName() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let result = OutputFileNamer().markdownURL(
            for: URL(fileURLWithPath: "/input/Report.final.docx"),
            in: directory
        )

        XCTAssertEqual(result.lastPathComponent, "Report.final.md")
    }

    func testAvoidsExistingAndReservedNames() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        FileManager.default.createFile(
            atPath: directory.appendingPathComponent("Report.md").path,
            contents: Data()
        )

        let result = OutputFileNamer().markdownURL(
            for: URL(fileURLWithPath: "/input/Report.pdf"),
            in: directory,
            reserved: ["Report-1.md"]
        )

        XCTAssertEqual(result.lastPathComponent, "Report-2.md")
    }
}
