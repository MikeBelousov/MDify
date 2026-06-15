import XCTest
@testable import MDifyCore

final class WorkerBundleResolverTests: XCTestCase {
    func testFindsExecutableWorkerInsideBundleResources() throws {
        let resources = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let workerDirectory = resources.appendingPathComponent("Workers/mdify-worker-ocr", isDirectory: true)
        let executable = workerDirectory.appendingPathComponent("mdify-worker-ocr")
        try FileManager.default.createDirectory(at: workerDirectory, withIntermediateDirectories: true)
        FileManager.default.createFile(atPath: executable.path, contents: Data())
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: executable.path)
        addTeardownBlock { try? FileManager.default.removeItem(at: resources) }

        let resolver = WorkerBundleResolver(bundleURL: resources, workerKind: .ocr)
        let status = resolver.status()

        XCTAssertEqual(status.kind, .ocr)
        XCTAssertEqual(status.executableURL, executable)
        XCTAssertTrue(status.isExecutable)
    }

    func testOCRStatusReadsModelManifestAndChecksModelFiles() throws {
        let resources = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let workerDirectory = resources.appendingPathComponent("Workers/mdify-worker-ocr", isDirectory: true)
        let executable = workerDirectory.appendingPathComponent("mdify-worker-ocr")
        let manifestDirectory = workerDirectory.appendingPathComponent("_internal/workers/ocr", isDirectory: true)
        let modelsDirectory = manifestDirectory.appendingPathComponent("models", isDirectory: true)
        try FileManager.default.createDirectory(at: manifestDirectory, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: modelsDirectory.appendingPathComponent("det"), withIntermediateDirectories: true)
        FileManager.default.createFile(atPath: executable.path, contents: Data())
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: executable.path)
        try """
        {
          "version": "test-models",
          "files": [
            {"path": "det/model.onnx", "sha256": "unused"}
          ]
        }
        """.write(to: manifestDirectory.appendingPathComponent("model_manifest.json"), atomically: true, encoding: .utf8)
        FileManager.default.createFile(atPath: modelsDirectory.appendingPathComponent("det/model.onnx").path, contents: Data())
        addTeardownBlock { try? FileManager.default.removeItem(at: resources) }

        let status = WorkerBundleResolver(bundleURL: resources, workerKind: .ocr).status()

        XCTAssertEqual(status.modelManifestVersion, "test-models")
        XCTAssertEqual(status.modelManifestURL, manifestDirectory.appendingPathComponent("model_manifest.json"))
        XCTAssertTrue(status.modelsPresent)
    }

    func testLiteStatusDoesNotRequireOCRModels() throws {
        let resources = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let workerDirectory = resources.appendingPathComponent("Workers/mdify-worker-lite", isDirectory: true)
        let executable = workerDirectory.appendingPathComponent("mdify-worker-lite")
        try FileManager.default.createDirectory(at: workerDirectory, withIntermediateDirectories: true)
        FileManager.default.createFile(atPath: executable.path, contents: Data())
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: executable.path)
        addTeardownBlock { try? FileManager.default.removeItem(at: resources) }

        let status = WorkerBundleResolver(bundleURL: resources, workerKind: .lite).status()

        XCTAssertNil(status.modelManifestVersion)
        XCTAssertNil(status.modelManifestURL)
        XCTAssertTrue(status.modelsPresent)
    }

    func testMakeClientPreservesExplicitOCRMode() {
        let resources = URL(fileURLWithPath: "/tmp/TestResources", isDirectory: true)
        let resolver = WorkerBundleResolver(bundleURL: resources, workerKind: .ocr)

        let client = resolver.makeClient(ocrMode: .off)

        XCTAssertEqual(client.kind, .ocr)
        XCTAssertEqual(client.ocrMode, .off)
    }

    func testLiteVariantBuildsNativeRoutingClient() {
        let resolver = WorkerBundleResolver(
            bundleURL: URL(fileURLWithPath: "/tmp/TestResources", isDirectory: true),
            workerKind: .lite
        )
        var nativeOCRCreationCount = 0

        let route = resolver.makeConversionRoute(nativeOCRFactory: {
            nativeOCRCreationCount += 1
            return VisionOCRService()
        })

        XCTAssertEqual(route.kind, .nativeLite)
        XCTAssertTrue(route.client is NativeOCRRoutingClient)
        XCTAssertEqual(nativeOCRCreationCount, 1)
    }

    func testOCRVariantBuildsDirectWorkerRoute() {
        let resolver = WorkerBundleResolver(
            bundleURL: URL(fileURLWithPath: "/tmp/TestResources", isDirectory: true),
            workerKind: .ocr
        )

        let route = resolver.makeConversionRoute()

        XCTAssertEqual(route.kind, .directOCRWorker)
        let client = route.client as? WorkerClient
        XCTAssertEqual(client?.kind, .ocr)
        XCTAssertEqual(client?.ocrMode, .auto)
    }

    func testOCRVariantDoesNotCreateNativeOCR() {
        let resolver = WorkerBundleResolver(
            bundleURL: URL(fileURLWithPath: "/tmp/TestResources", isDirectory: true),
            workerKind: .ocr
        )
        var nativeOCRCreationCount = 0

        _ = resolver.makeConversionRoute(nativeOCRFactory: {
            nativeOCRCreationCount += 1
            return VisionOCRService()
        })

        XCTAssertEqual(nativeOCRCreationCount, 0)
    }
}
