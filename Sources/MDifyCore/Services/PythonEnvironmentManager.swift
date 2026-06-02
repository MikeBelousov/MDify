import Foundation

public struct PythonEnvironmentManager: Sendable {
    public let paths: AppPaths
    public let runner: any ProcessRunning
    public let candidatePaths: [String]

    public init(
        paths: AppPaths = AppPaths(),
        runner: any ProcessRunning = ProcessRunner(),
        candidatePaths: [String] = PythonEnvironmentManager.defaultCandidatePaths
    ) {
        self.paths = paths
        self.runner = runner
        self.candidatePaths = candidatePaths
    }

    public static let defaultCandidatePaths = [
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/opt/anaconda3/bin/python3",
        "/usr/bin/python3"
    ]

    public func discoverPython() async -> PythonCandidate? {
        var candidates: [PythonCandidate] = []

        for path in candidatePaths {
            if let candidate = await inspectPython(at: URL(fileURLWithPath: path)) {
                candidates.append(candidate)
            }
        }

        if let envCandidate = await discoverFromEnvironment(),
           !candidates.contains(where: { $0.executableURL.path == envCandidate.executableURL.path }) {
            candidates.append(envCandidate)
        }

        return bestCandidate(from: candidates)
    }

    public func bestCandidate(from candidates: [PythonCandidate]) -> PythonCandidate? {
        let supported = candidates.filter { $0.version.isSupported }
        let native = supported.filter { $0.architecture == .host }
        return (native.isEmpty ? supported : native).sorted {
            if $0.version != $1.version { return $0.version > $1.version }
            return $0.executableURL.path < $1.executableURL.path
        }.first
    }

    public func createVirtualEnvironment(using python: PythonCandidate) async throws -> ProcessResult {
        try paths.ensureDirectories()
        if FileManager.default.fileExists(atPath: paths.venvPythonURL.path) {
            if let existing = await inspectPython(at: paths.venvPythonURL), existing.version.isSupported {
                return ProcessResult(exitCode: 0, stdout: "Existing venv reused.", stderr: "")
            }
            try FileManager.default.removeItem(at: paths.venvDirectory)
        }

        return try await runner.run(
            executableURL: python.executableURL,
            arguments: ["-m", "venv", paths.venvDirectory.path],
            environment: nil
        )
    }

    public func inspectPython(at executableURL: URL) async -> PythonCandidate? {
        guard FileManager.default.isExecutableFile(atPath: executableURL.path) else {
            return nil
        }

        do {
            let versionResult = try await runner.run(
                executableURL: executableURL,
                arguments: ["--version"],
                environment: nil
            )
            let versionOutput = versionResult.stdout + versionResult.stderr
            guard versionResult.exitCode == 0,
                  let version = PythonVersion(versionOutput),
                  version.isSupported else {
                return nil
            }

            let archResult = try await runner.run(
                executableURL: executableURL,
                arguments: ["-c", "import platform; print(platform.machine())"],
                environment: nil
            )
            let architecture = PythonArchitecture(machine: archResult.stdout)
            return PythonCandidate(executableURL: executableURL, version: version, architecture: architecture)
        } catch {
            return nil
        }
    }

    private func discoverFromEnvironment() async -> PythonCandidate? {
        let envURL = URL(fileURLWithPath: "/usr/bin/env")
        do {
            let result = try await runner.run(
                executableURL: envURL,
                arguments: ["python3", "-c", "import sys; print(sys.executable)"],
                environment: nil
            )
            guard result.exitCode == 0 else { return nil }
            let path = result.stdout.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !path.isEmpty else { return nil }
            return await inspectPython(at: URL(fileURLWithPath: path))
        } catch {
            return nil
        }
    }
}
