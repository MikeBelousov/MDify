import Foundation

public enum MarkItDownInstallState: Equatable, Sendable {
    case missing
    case installed(version: String)
    case wrongVersion(version: String)
}

public struct MarkItDownInstaller: Sendable {
    public static let pinnedRequirement = "markitdown[all]==0.1.6"
    public static let pinnedVersion = "0.1.6"

    public let paths: AppPaths
    public let runner: any ProcessRunning

    public init(paths: AppPaths = AppPaths(), runner: any ProcessRunning = ProcessRunner()) {
        self.paths = paths
        self.runner = runner
    }

    public func checkInstalledVersion() async -> MarkItDownInstallState {
        guard FileManager.default.isExecutableFile(atPath: paths.venvPythonURL.path) else {
            return .missing
        }

        do {
            let result = try await runner.run(
                executableURL: paths.venvPythonURL,
                arguments: [
                    "-c",
                    "import importlib.metadata as m; print(m.version('markitdown'))"
                ],
                environment: nil
            )
            guard result.exitCode == 0 else { return .missing }
            let version = result.stdout.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !version.isEmpty else { return .missing }
            return version == Self.pinnedVersion ? .installed(version: version) : .wrongVersion(version: version)
        } catch {
            return .missing
        }
    }

    public func install() async throws -> String {
        var log = ""
        let upgrade = try await runner.run(
            executableURL: paths.venvPythonURL,
            arguments: ["-m", "pip", "install", "--upgrade", "pip"],
            environment: ["PIP_DISABLE_PIP_VERSION_CHECK": "1"]
        )
        log += upgrade.stdout + upgrade.stderr
        guard upgrade.exitCode == 0 else {
            throw MarkItDownInstallerError.installFailed(log)
        }

        let install = try await runner.run(
            executableURL: paths.venvPythonURL,
            arguments: ["-m", "pip", "install", Self.pinnedRequirement],
            environment: ["PIP_DISABLE_PIP_VERSION_CHECK": "1"]
        )
        log += install.stdout + install.stderr
        guard install.exitCode == 0 else {
            throw MarkItDownInstallerError.installFailed(log)
        }

        return log
    }
}

public enum MarkItDownInstallerError: LocalizedError, Equatable {
    case installFailed(String)

    public var errorDescription: String? {
        switch self {
        case .installFailed:
            "MarkItDown installation failed."
        }
    }
}
