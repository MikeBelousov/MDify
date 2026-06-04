import Foundation

public enum WorkerOCRMode: String, Equatable, Sendable {
    case auto
    case always
    case off
}

public protocol WorkerConverting: Sendable {
    func convert(inputURL: URL, outputURL: URL) async throws -> WorkerResponse
}

public struct WorkerClient: WorkerConverting {
    public let executableURL: URL
    public let kind: WorkerKind
    public let ocrMode: WorkerOCRMode
    public let runner: any ProcessRunning

    public init(
        executableURL: URL,
        kind: WorkerKind,
        ocrMode: WorkerOCRMode = .auto,
        runner: any ProcessRunning = ProcessRunner()
    ) {
        self.executableURL = executableURL
        self.kind = kind
        self.ocrMode = ocrMode
        self.runner = runner
    }

    public func convert(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        var arguments = [
            "--input", inputURL.path,
            "--output", outputURL.path,
            "--format", "json"
        ]
        if kind == .ocr {
            arguments += ["--ocr", ocrMode.rawValue, "--ocr-lang", "cyrillic", "--dpi", "300"]
        }

        let result = try await runner.run(
            executableURL: executableURL,
            arguments: arguments,
            environment: nil
        )

        guard let data = result.stdout.data(using: .utf8), !data.isEmpty else {
            throw WorkerClientError.emptyResponse(result.stderr)
        }

        do {
            return try JSONDecoder().decode(WorkerResponse.self, from: data)
        } catch {
            throw WorkerClientError.invalidJSON(result.stdout + result.stderr)
        }
    }
}

public enum WorkerClientError: LocalizedError, Equatable {
    case emptyResponse(String)
    case invalidJSON(String)

    public var errorDescription: String? {
        switch self {
        case .emptyResponse(let stderr):
            stderr.isEmpty ? "Worker did not return JSON." : stderr
        case .invalidJSON:
            "Worker returned invalid JSON."
        }
    }
}
