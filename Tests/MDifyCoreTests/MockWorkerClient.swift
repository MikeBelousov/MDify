import Foundation
@testable import MDifyCore

actor MockWorkerClient: WorkerConverting {
    enum Behavior: Sendable {
        case success(String, engine: String = "markitdown", ocrUsed: Bool = false)
        case failure(String, code: String)
    }

    private let behaviors: [String: Behavior]

    init(behaviors: [String: Behavior]) {
        self.behaviors = behaviors
    }

    func convert(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        let behavior = behaviors[inputURL.lastPathComponent] ?? .success("# Default\n")
        switch behavior {
        case .success(let markdown, let engine, let ocrUsed):
            try FileManager.default.createDirectory(
                at: outputURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try markdown.write(to: outputURL, atomically: true, encoding: .utf8)
            return WorkerResponse(
                ok: true,
                outputPath: outputURL.path,
                inputPath: inputURL.path,
                worker: ocrUsed ? "ocr" : "lite",
                engine: engine,
                ocrUsed: ocrUsed,
                warnings: [],
                errorCode: nil,
                message: nil
            )
        case .failure(let message, let code):
            return WorkerResponse(
                ok: false,
                outputPath: nil,
                inputPath: inputURL.path,
                worker: "lite",
                engine: nil,
                ocrUsed: false,
                warnings: [],
                errorCode: code,
                message: message
            )
        }
    }
}
