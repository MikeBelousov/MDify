import XCTest
@testable import MDifyCore

final class WorkerClientTests: XCTestCase {
    func testLiteWorkerDecodesJSONResponse() async throws {
        let response = """
        {"ok":true,"output_path":"/tmp/out.md","input_path":"/tmp/input.txt","worker":"lite","engine":"markitdown","ocr_used":false,"warnings":[]}
        """
        let client = WorkerClient(
            executableURL: URL(fileURLWithPath: "/tmp/mdify-worker-lite"),
            kind: .lite,
            runner: MockRunner(results: [
                "mdify-worker-lite": ProcessResult(exitCode: 0, stdout: response, stderr: "")
            ])
        )

        let result = try await client.convert(
            inputURL: URL(fileURLWithPath: "/tmp/input.txt"),
            outputURL: URL(fileURLWithPath: "/tmp/out.md")
        )

        XCTAssertTrue(result.ok)
        XCTAssertEqual(result.worker, "lite")
        XCTAssertEqual(result.engine, "markitdown")
        XCTAssertFalse(result.ocrUsed)
    }

    func testOCRWorkerPassesOCRArguments() async throws {
        final class InvocationBox: @unchecked Sendable {
            var arguments: [String] = []
        }
        let box = InvocationBox()
        let response = """
        {"ok":true,"output_path":"/tmp/out.md","input_path":"/tmp/input.png","worker":"ocr","engine":"rapidocr","ocr_used":true,"warnings":[]}
        """
        let client = WorkerClient(
            executableURL: URL(fileURLWithPath: "/tmp/mdify-worker-ocr"),
            kind: .ocr,
            runner: MockRunner(
                results: [
                    "mdify-worker-ocr": ProcessResult(exitCode: 0, stdout: response, stderr: "")
                ],
                onRun: { _, arguments, _ in box.arguments = arguments }
            )
        )

        _ = try await client.convert(
            inputURL: URL(fileURLWithPath: "/tmp/input.png"),
            outputURL: URL(fileURLWithPath: "/tmp/out.md")
        )

        XCTAssertEqual(box.arguments, [
            "--input", "/tmp/input.png",
            "--output", "/tmp/out.md",
            "--format", "json",
            "--ocr", "auto",
            "--ocr-lang", "cyrillic",
            "--dpi", "300"
        ])
    }

    func testOCRWorkerPassesExplicitOCRModes() async throws {
        final class InvocationBox: @unchecked Sendable {
            var invocations: [[String]] = []
        }
        let box = InvocationBox()
        let response = """
        {"ok":true,"output_path":"/tmp/out.md","input_path":"/tmp/input.pdf","worker":"ocr","engine":"markitdown","ocr_used":false,"warnings":[]}
        """

        for mode in [WorkerOCRMode.off, .always] {
            let client = WorkerClient(
                executableURL: URL(fileURLWithPath: "/tmp/mdify-worker-ocr"),
                kind: .ocr,
                ocrMode: mode,
                runner: MockRunner(
                    results: [
                        "mdify-worker-ocr": ProcessResult(exitCode: 0, stdout: response, stderr: "")
                    ],
                    onRun: { _, arguments, _ in box.invocations.append(arguments) }
                )
            )

            _ = try await client.convert(
                inputURL: URL(fileURLWithPath: "/tmp/input.pdf"),
                outputURL: URL(fileURLWithPath: "/tmp/out.md")
            )
        }

        XCTAssertEqual(box.invocations[0].suffix(6), [
            "--ocr", "off",
            "--ocr-lang", "cyrillic",
            "--dpi", "300"
        ])
        XCTAssertEqual(box.invocations[1].suffix(6), [
            "--ocr", "always",
            "--ocr-lang", "cyrillic",
            "--dpi", "300"
        ])
    }

    func testInvalidJSONThrowsWorkerClientError() async throws {
        let client = WorkerClient(
            executableURL: URL(fileURLWithPath: "/tmp/mdify-worker-lite"),
            kind: .lite,
            runner: MockRunner(results: [
                "mdify-worker-lite": ProcessResult(exitCode: 0, stdout: "not-json", stderr: "")
            ])
        )

        do {
            _ = try await client.convert(
                inputURL: URL(fileURLWithPath: "/tmp/input.txt"),
                outputURL: URL(fileURLWithPath: "/tmp/out.md")
            )
            XCTFail("Expected invalid JSON to throw")
        } catch let error as WorkerClientError {
            XCTAssertEqual(error, .invalidJSON("not-json"))
        }
    }
}
