import XCTest
@testable import MDifyCore

final class PythonVersionTests: XCTestCase {
    func testParsesPythonVersionOutput() {
        XCTAssertEqual(PythonVersion("Python 3.13.5"), PythonVersion(major: 3, minor: 13, patch: 5))
        XCTAssertEqual(PythonVersion("Python 3.10"), PythonVersion(major: 3, minor: 10, patch: 0))
    }

    func testRejectsUnsupportedVersions() {
        XCTAssertFalse(PythonVersion("Python 3.9.9")!.isSupported)
        XCTAssertTrue(PythonVersion("Python 3.10.0")!.isSupported)
        XCTAssertTrue(PythonVersion("Python 3.13.5")!.isSupported)
        XCTAssertFalse(PythonVersion("Python 3.14.0")!.isSupported)
    }

    func testChoosesNewestNativePython() {
        let manager = PythonEnvironmentManager(
            runner: MockRunner(results: [:]),
            candidatePaths: []
        )
        let olderNative = PythonCandidate(
            executableURL: URL(fileURLWithPath: "/a/python3"),
            version: PythonVersion(major: 3, minor: 11, patch: 0),
            architecture: .host
        )
        let newerNative = PythonCandidate(
            executableURL: URL(fileURLWithPath: "/b/python3"),
            version: PythonVersion(major: 3, minor: 13, patch: 0),
            architecture: .host
        )
        let wrongArch = PythonCandidate(
            executableURL: URL(fileURLWithPath: "/c/python3"),
            version: PythonVersion(major: 3, minor: 14, patch: 0),
            architecture: PythonArchitecture.host == .arm64 ? .x86_64 : .arm64
        )

        XCTAssertEqual(manager.bestCandidate(from: [olderNative, newerNative, wrongArch]), newerNative)
    }
}
