import Foundation

public struct PythonCandidate: Equatable, Sendable {
    public let executableURL: URL
    public let version: PythonVersion
    public let architecture: PythonArchitecture

    public init(executableURL: URL, version: PythonVersion, architecture: PythonArchitecture) {
        self.executableURL = executableURL
        self.version = version
        self.architecture = architecture
    }
}
