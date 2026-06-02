import Foundation

public enum ConversionStatus: String, Codable, CaseIterable, Equatable, Sendable {
    case pending
    case converting
    case succeeded
    case failed
    case cancelled

    public var title: String {
        switch self {
        case .pending: "Pending"
        case .converting: "Converting"
        case .succeeded: "Done"
        case .failed: "Failed"
        case .cancelled: "Cancelled"
        }
    }
}
