import Foundation

public enum PythonArchitecture: String, Codable, Equatable, Sendable {
    case arm64
    case x86_64
    case unknown

    public init(machine: String) {
        let normalized = machine.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        switch normalized {
        case "arm64", "aarch64":
            self = .arm64
        case "x86_64", "amd64":
            self = .x86_64
        default:
            self = .unknown
        }
    }

    public static var host: PythonArchitecture {
        #if arch(arm64)
        return .arm64
        #elseif arch(x86_64)
        return .x86_64
        #else
        return .unknown
        #endif
    }
}
