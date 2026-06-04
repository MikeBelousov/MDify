import Foundation

public struct WorkerResponse: Codable, Equatable, Sendable {
    public let ok: Bool
    public let outputPath: String?
    public let inputPath: String
    public let worker: String
    public let engine: String?
    public let ocrUsed: Bool
    public let warnings: [String]
    public let errorCode: String?
    public let message: String?

    enum CodingKeys: String, CodingKey {
        case ok
        case outputPath = "output_path"
        case inputPath = "input_path"
        case worker
        case engine
        case ocrUsed = "ocr_used"
        case warnings
        case errorCode = "error_code"
        case message
    }

    public init(
        ok: Bool,
        outputPath: String?,
        inputPath: String,
        worker: String,
        engine: String?,
        ocrUsed: Bool,
        warnings: [String],
        errorCode: String?,
        message: String?
    ) {
        self.ok = ok
        self.outputPath = outputPath
        self.inputPath = inputPath
        self.worker = worker
        self.engine = engine
        self.ocrUsed = ocrUsed
        self.warnings = warnings
        self.errorCode = errorCode
        self.message = message
    }
}
