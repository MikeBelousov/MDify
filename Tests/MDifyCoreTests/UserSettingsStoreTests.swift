import Foundation
import XCTest
@testable import MDifyCore

final class UserSettingsStoreTests: XCTestCase {
    func testOCRVariantDefaultsToAutoAndPersistsSelection() {
        let defaults = makeUserDefaults()
        let store = UserSettingsStore(workerKind: .ocr, userDefaults: defaults)

        XCTAssertEqual(store.ocrLanguageMode, .auto)

        store.ocrLanguageMode = .cyrillic

        let relaunchedStore = UserSettingsStore(workerKind: .ocr, userDefaults: defaults)
        XCTAssertEqual(relaunchedStore.ocrLanguageMode, .cyrillic)
    }

    func testLiteVariantIgnoresSavedLanguageAndDoesNotChangeIt() {
        let defaults = makeUserDefaults()
        let ocrStore = UserSettingsStore(workerKind: .ocr, userDefaults: defaults)
        ocrStore.ocrLanguageMode = .latin

        let liteStore = UserSettingsStore(workerKind: .lite, userDefaults: defaults)
        XCTAssertEqual(liteStore.ocrLanguageMode, .auto)

        liteStore.ocrLanguageMode = .cyrillic

        XCTAssertEqual(ocrStore.ocrLanguageMode, .latin)
    }

    func testInvalidSavedLanguageFallsBackToAuto() {
        let defaults = makeUserDefaults()
        defaults.set("unsupported", forKey: UserSettingsStore.ocrLanguageModeKey)

        let store = UserSettingsStore(workerKind: .ocr, userDefaults: defaults)

        XCTAssertEqual(store.ocrLanguageMode, .auto)
    }

    private func makeUserDefaults() -> UserDefaults {
        let suiteName = "UserSettingsStoreTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defaults.removePersistentDomain(forName: suiteName)
        addTeardownBlock {
            defaults.removePersistentDomain(forName: suiteName)
        }
        return defaults
    }
}
