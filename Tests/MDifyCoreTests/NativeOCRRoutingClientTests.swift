import Foundation
import XCTest
@testable import MDifyCore

final class NativeOCRRoutingClientTests: XCTestCase {
    func testLiteImageUsesNativeVisionAndDoesNotCallWorker() async throws {
        let directory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let inputURL = directory.appendingPathComponent("scan.png")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())
        let outputURL = directory.appendingPathComponent("scan.md")
        let worker = SpyWorkerClient(markdown: "# Worker\n")
        let native = StubNativeOCR(result: NativeOCRResult(markdown: "Native recognized text\n", averageConfidence: 0.9))
        let client = NativeOCRRoutingClient(workerKind: .lite, workerClient: worker, nativeOCR: native)

        let response = try await client.convert(inputURL: inputURL, outputURL: outputURL)

        XCTAssertEqual(response.worker, "native")
        XCTAssertEqual(response.engine, "apple-vision")
        XCTAssertTrue(response.ocrUsed)
        XCTAssertEqual(try String(contentsOf: outputURL, encoding: .utf8), "Native recognized text\n")
        let workerInvocationCount = await worker.invocationCount
        XCTAssertEqual(workerInvocationCount, 0)
    }

    func testLiteImageKeepsWeakNonEmptyNativeResultWithWarning() async throws {
        let directory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let inputURL = directory.appendingPathComponent("scan.png")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())
        let outputURL = directory.appendingPathComponent("scan.md")
        let worker = SpyWorkerClient(markdown: "# Worker\n")
        let native = StubNativeOCR(result: NativeOCRResult(markdown: "tiny\n", averageConfidence: 0.2))
        let client = NativeOCRRoutingClient(workerKind: .lite, workerClient: worker, nativeOCR: native)

        let response = try await client.convert(inputURL: inputURL, outputURL: outputURL)

        XCTAssertEqual(response.worker, "native")
        XCTAssertTrue(response.warnings.contains { $0.contains("Apple Vision OCR confidence was low") })
        XCTAssertEqual(try String(contentsOf: outputURL, encoding: .utf8), "tiny\n")
        let workerInvocationCount = await worker.invocationCount
        XCTAssertEqual(workerInvocationCount, 0)
    }

    func testLiteImageFailsWhenNativeOCRReturnsNoText() async throws {
        let directory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let inputURL = directory.appendingPathComponent("blank.png")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())
        let outputURL = directory.appendingPathComponent("blank.md")
        let worker = SpyWorkerClient(markdown: "# Worker\n")
        let native = StubNativeOCR(result: NativeOCRResult(markdown: "", averageConfidence: 0))
        let client = NativeOCRRoutingClient(workerKind: .lite, workerClient: worker, nativeOCR: native)

        do {
            _ = try await client.convert(inputURL: inputURL, outputURL: outputURL)
            XCTFail("Expected empty native OCR to fail in Lite")
        } catch let error as NativeOCRRoutingError {
            XCTAssertEqual(error, .nativeOCRReturnedNoText)
        }

        let workerInvocationCount = await worker.invocationCount
        XCTAssertEqual(workerInvocationCount, 0)
        XCTAssertFalse(FileManager.default.fileExists(atPath: outputURL.path))
    }

    func testOCRImageFallsBackToRapidOCRWhenNativeResultIsWeak() async throws {
        let directory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let inputURL = directory.appendingPathComponent("scan.jpg")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())
        let outputURL = directory.appendingPathComponent("scan.md")
        let preflight = SpyWorkerClient(markdown: "# Preflight\n")
        let fallback = SpyWorkerClient(markdown: "# RapidOCR\n", engine: "rapidocr", ocrUsed: true)
        let native = StubNativeOCR(result: NativeOCRResult(markdown: "tiny\n", averageConfidence: 0.2))
        let client = NativeOCRRoutingClient(
            workerKind: .ocr,
            workerClient: preflight,
            rapidOCRWorkerClient: fallback,
            nativeOCR: native
        )

        let response = try await client.convert(inputURL: inputURL, outputURL: outputURL)

        XCTAssertEqual(response.worker, "ocr")
        XCTAssertEqual(response.engine, "rapidocr")
        XCTAssertTrue(response.warnings.contains { $0.contains("Apple Vision OCR was weak") })
        XCTAssertEqual(try String(contentsOf: outputURL, encoding: .utf8), "# RapidOCR\n")
        let preflightInvocationCount = await preflight.invocationCount
        let fallbackInvocationCount = await fallback.invocationCount
        XCTAssertEqual(preflightInvocationCount, 0)
        XCTAssertEqual(fallbackInvocationCount, 1)
    }

    func testTextPDFUsesMarkItDownPreflightAndSkipsNativeOCR() async throws {
        let directory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let inputURL = directory.appendingPathComponent("text.pdf")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())
        let outputURL = directory.appendingPathComponent("text.md")
        let worker = SpyWorkerClient(markdown: "This PDF already has enough extracted text.\n")
        let native = StubNativeOCR(result: NativeOCRResult(markdown: "Native should not run\n", averageConfidence: 0.9))
        let client = NativeOCRRoutingClient(workerKind: .ocr, workerClient: worker, nativeOCR: native)

        let response = try await client.convert(inputURL: inputURL, outputURL: outputURL)

        XCTAssertEqual(response.worker, "ocr")
        XCTAssertEqual(response.engine, "markitdown")
        XCTAssertFalse(response.ocrUsed)
        let workerInvocationCount = await worker.invocationCount
        let nativeInvocationCount = await native.invocationCount
        XCTAssertEqual(workerInvocationCount, 1)
        XCTAssertEqual(nativeInvocationCount, 0)
    }

    func testScannedPDFUsesNativeOCRAndFallsBackToRapidOCRWhenNativeIsWeak() async throws {
        let directory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let inputURL = directory.appendingPathComponent("scan.pdf")
        FileManager.default.createFile(atPath: inputURL.path, contents: Data())
        let outputURL = directory.appendingPathComponent("scan.md")
        let preflight = SpyWorkerClient(markdown: "\n")
        let fallback = SpyWorkerClient(markdown: "# Rapid PDF\n", engine: "rapidocr", ocrUsed: true)
        let native = StubNativeOCR(result: NativeOCRResult(markdown: "bad\n", averageConfidence: 0.3))
        let client = NativeOCRRoutingClient(
            workerKind: .ocr,
            workerClient: preflight,
            rapidOCRWorkerClient: fallback,
            nativeOCR: native
        )

        let response = try await client.convert(inputURL: inputURL, outputURL: outputURL)

        XCTAssertEqual(response.engine, "rapidocr")
        let preflightInvocationCount = await preflight.invocationCount
        let nativeInvocationCount = await native.invocationCount
        let fallbackInvocationCount = await fallback.invocationCount
        XCTAssertEqual(preflightInvocationCount, 1)
        XCTAssertEqual(nativeInvocationCount, 1)
        XCTAssertEqual(fallbackInvocationCount, 1)
    }

    private func makeTemporaryDirectory() throws -> URL {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory
    }
}

private actor SpyWorkerClient: WorkerConverting {
    private(set) var invocationCount = 0
    private let markdown: String
    private let engine: String
    private let ocrUsed: Bool

    init(markdown: String, engine: String = "markitdown", ocrUsed: Bool = false) {
        self.markdown = markdown
        self.engine = engine
        self.ocrUsed = ocrUsed
    }

    func convert(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        invocationCount += 1
        try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try markdown.write(to: outputURL, atomically: true, encoding: .utf8)
        return WorkerResponse(
            ok: true,
            outputPath: outputURL.path,
            inputPath: inputURL.path,
            worker: ocrUsed ? "ocr" : "ocr",
            engine: engine,
            ocrUsed: ocrUsed,
            warnings: [],
            errorCode: nil,
            message: nil
        )
    }
}

private actor StubNativeOCR: NativeOCRRecognizing {
    private(set) var invocationCount = 0
    private let result: NativeOCRResult

    init(result: NativeOCRResult) {
        self.result = result
    }

    func recognize(inputURL: URL) async throws -> NativeOCRResult {
        invocationCount += 1
        return result
    }
}
