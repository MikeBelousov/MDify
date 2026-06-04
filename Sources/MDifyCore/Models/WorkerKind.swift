import Foundation

public enum WorkerKind: String, Codable, Equatable, Sendable {
    case lite
    case ocr

    public var executableName: String {
        "mdify-worker-\(rawValue)"
    }

    public var displayName: String {
        switch self {
        case .lite: "MDify Lite"
        case .ocr: "MDify OCR"
        }
    }
}
