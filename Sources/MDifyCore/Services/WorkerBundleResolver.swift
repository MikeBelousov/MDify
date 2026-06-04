import Foundation

public struct WorkerBundleStatus: Equatable, Sendable {
    public let kind: WorkerKind
    public let executableURL: URL
    public let isExecutable: Bool
    public let modelManifestURL: URL?
    public let modelManifestVersion: String?
    public let modelsPresent: Bool

    public init(
        kind: WorkerKind,
        executableURL: URL,
        isExecutable: Bool,
        modelManifestURL: URL? = nil,
        modelManifestVersion: String? = nil,
        modelsPresent: Bool = true
    ) {
        self.kind = kind
        self.executableURL = executableURL
        self.isExecutable = isExecutable
        self.modelManifestURL = modelManifestURL
        self.modelManifestVersion = modelManifestVersion
        self.modelsPresent = modelsPresent
    }
}

public struct WorkerBundleResolver {
    public let bundleURL: URL
    public let workerKind: WorkerKind
    public let fileManager: FileManager

    public init(
        bundleURL: URL = Bundle.main.resourceURL ?? URL(fileURLWithPath: "."),
        workerKind: WorkerKind = WorkerBundleResolver.bundleWorkerKind(),
        fileManager: FileManager = .default
    ) {
        self.bundleURL = bundleURL
        self.workerKind = workerKind
        self.fileManager = fileManager
    }

    public func status() -> WorkerBundleStatus {
        let executableURL = workerExecutableURL()
        let modelStatus = modelStatus(for: executableURL)
        return WorkerBundleStatus(
            kind: workerKind,
            executableURL: executableURL,
            isExecutable: fileManager.isExecutableFile(atPath: executableURL.path),
            modelManifestURL: modelStatus.manifestURL,
            modelManifestVersion: modelStatus.version,
            modelsPresent: modelStatus.modelsPresent
        )
    }

    public func makeClient(
        ocrMode: WorkerOCRMode = .auto,
        runner: any ProcessRunning = ProcessRunner()
    ) -> WorkerClient {
        WorkerClient(executableURL: workerExecutableURL(), kind: workerKind, ocrMode: ocrMode, runner: runner)
    }

    public func makeNativeRoutingClient(
        runner: any ProcessRunning = ProcessRunner(),
        nativeOCR: any NativeOCRRecognizing = VisionOCRService()
    ) -> NativeOCRRoutingClient {
        let workerClient = makeClient(ocrMode: workerKind == .ocr ? .off : .auto, runner: runner)
        let rapidOCRWorkerClient: (any WorkerConverting)?
        if workerKind == .ocr {
            rapidOCRWorkerClient = makeClient(ocrMode: .always, runner: runner)
        } else {
            rapidOCRWorkerClient = nil
        }
        return NativeOCRRoutingClient(
            workerKind: workerKind,
            workerClient: workerClient,
            rapidOCRWorkerClient: rapidOCRWorkerClient,
            nativeOCR: nativeOCR
        )
    }

    private func workerExecutableURL() -> URL {
        if let override = ProcessInfo.processInfo.environment["MDIFY_WORKER_PATH"], !override.isEmpty {
            return URL(fileURLWithPath: override)
        }
        return bundleURL
            .appendingPathComponent("Workers", isDirectory: true)
            .appendingPathComponent(workerKind.executableName, isDirectory: true)
            .appendingPathComponent(workerKind.executableName)
    }

    private func modelStatus(for executableURL: URL) -> (manifestURL: URL?, version: String?, modelsPresent: Bool) {
        guard workerKind == .ocr else {
            return (nil, nil, true)
        }

        guard let manifestURL = modelManifestURL(for: executableURL),
              let data = try? Data(contentsOf: manifestURL),
              let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return (nil, nil, false)
        }

        let modelsDirectory = manifestURL.deletingLastPathComponent().appendingPathComponent("models", isDirectory: true)
        let files = payload["files"] as? [[String: Any]] ?? []
        let allFilesPresent = files.allSatisfy { entry in
            guard let path = entry["path"] as? String else { return false }
            return fileManager.fileExists(atPath: modelsDirectory.appendingPathComponent(path).path)
        }
        return (manifestURL, payload["version"] as? String, allFilesPresent)
    }

    private func modelManifestURL(for executableURL: URL) -> URL? {
        let workerDirectory = executableURL.deletingLastPathComponent()
        let candidates = [
            workerDirectory.appendingPathComponent("_internal/workers/ocr/model_manifest.json"),
            workerDirectory.appendingPathComponent("workers/ocr/model_manifest.json"),
            workerDirectory.appendingPathComponent("model_manifest.json")
        ]
        return candidates.first { fileManager.fileExists(atPath: $0.path) }
    }

    public static func bundleWorkerKind() -> WorkerKind {
        guard let rawValue = Bundle.main.infoDictionary?["MDifyWorkerKind"] as? String else {
            return .lite
        }
        return WorkerKind(rawValue: rawValue) ?? .lite
    }
}
