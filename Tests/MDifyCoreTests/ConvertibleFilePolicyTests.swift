import XCTest
@testable import MDifyCore

final class ConvertibleFilePolicyTests: XCTestCase {
    func testLitePolicyIncludesImageInputsForNativeVisionOCR() {
        let policy = ConvertibleFilePolicy(workerKind: .lite)

        XCTAssertTrue(policy.isConvertibleFile(URL(fileURLWithPath: "/tmp/report.pdf")))
        XCTAssertTrue(policy.isConvertibleFile(URL(fileURLWithPath: "/tmp/slides.pptx")))
        XCTAssertTrue(policy.isConvertibleFile(URL(fileURLWithPath: "/tmp/scan.png")))
    }

    func testOCRPolicyIncludesImageInputs() {
        let policy = ConvertibleFilePolicy(workerKind: .ocr)

        XCTAssertTrue(policy.isConvertibleFile(URL(fileURLWithPath: "/tmp/report.pdf")))
        XCTAssertTrue(policy.isConvertibleFile(URL(fileURLWithPath: "/tmp/scan.png")))
        XCTAssertTrue(policy.isConvertibleFile(URL(fileURLWithPath: "/tmp/photo.jpeg")))
    }
}
