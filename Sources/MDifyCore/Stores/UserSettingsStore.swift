import Foundation

public struct UserSettingsStore {
    static let ocrLanguageModeKey = "ocrLanguageMode"

    private let workerKind: WorkerKind
    private let userDefaults: UserDefaults

    public init(workerKind: WorkerKind, userDefaults: UserDefaults = .standard) {
        self.workerKind = workerKind
        self.userDefaults = userDefaults
    }

    public var ocrLanguageMode: OCRLanguageMode {
        get {
            guard workerKind == .ocr,
                  let rawValue = userDefaults.string(forKey: Self.ocrLanguageModeKey),
                  let languageMode = OCRLanguageMode(rawValue: rawValue) else {
                return .auto
            }
            return languageMode
        }
        nonmutating set {
            guard workerKind == .ocr else { return }
            userDefaults.set(newValue.rawValue, forKey: Self.ocrLanguageModeKey)
        }
    }
}
