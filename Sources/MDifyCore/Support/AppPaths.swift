import Foundation

public struct AppPaths: Sendable {
    public let applicationSupportDirectory: URL

    public init(applicationSupportDirectory: URL? = nil) {
        if let applicationSupportDirectory {
            self.applicationSupportDirectory = applicationSupportDirectory
        } else {
            self.applicationSupportDirectory = FileManager.default
                .urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("MDify", isDirectory: true)
        }
    }

    public var pythonDirectory: URL {
        applicationSupportDirectory.appendingPathComponent("Python", isDirectory: true)
    }

    public var venvDirectory: URL {
        pythonDirectory.appendingPathComponent("venv", isDirectory: true)
    }

    public var venvPythonURL: URL {
        venvDirectory.appendingPathComponent("bin/python")
    }

    public var markitdownExecutableURL: URL {
        venvDirectory.appendingPathComponent("bin/markitdown")
    }

    public func ensureDirectories() throws {
        try FileManager.default.createDirectory(
            at: pythonDirectory,
            withIntermediateDirectories: true
        )
    }
}
