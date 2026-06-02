import XCTest
@testable import MDifyCore

final class OutputRevealPolicyTests: XCTestCase {
    func testRejectsItemsWithoutSucceededExistingOutput() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let outputURL = directory.appendingPathComponent("result.md")
        try "# Result".write(to: outputURL, atomically: true, encoding: .utf8)
        let policy = OutputRevealPolicy()

        XCTAssertFalse(policy.canRevealOutput(for: ConversionItem(
            inputURL: URL(fileURLWithPath: "/tmp/input.pdf"),
            status: .succeeded
        )))
        XCTAssertFalse(policy.canRevealOutput(for: ConversionItem(
            inputURL: URL(fileURLWithPath: "/tmp/input.pdf"),
            outputURL: outputURL,
            status: .pending
        )))
        XCTAssertFalse(policy.canRevealOutput(for: ConversionItem(
            inputURL: URL(fileURLWithPath: "/tmp/input.pdf"),
            outputURL: directory.appendingPathComponent("missing.md"),
            status: .succeeded
        )))
    }

    func testAllowsSucceededItemWithExistingOutputFile() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let outputURL = directory.appendingPathComponent("result.md")
        try "# Result".write(to: outputURL, atomically: true, encoding: .utf8)

        XCTAssertTrue(OutputRevealPolicy().canRevealOutput(for: ConversionItem(
            inputURL: URL(fileURLWithPath: "/tmp/input.pdf"),
            outputURL: outputURL,
            status: .succeeded
        )))
    }
}
