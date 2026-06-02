import Foundation
@testable import MDifyCore

struct MockRunner: ProcessRunning {
    let results: [String: ProcessResult]

    func run(
        executableURL: URL,
        arguments: [String],
        environment: [String: String]?
    ) async throws -> ProcessResult {
        let executableName = executableURL.lastPathComponent
        let lastArgumentName = arguments.last.map { URL(fileURLWithPath: $0).lastPathComponent } ?? ""
        if let result = results["\(executableName)|\(lastArgumentName)"] {
            return result
        }
        if let result = results[executableName] {
            return result
        }
        return ProcessResult(exitCode: 0, stdout: "", stderr: "")
    }
}
