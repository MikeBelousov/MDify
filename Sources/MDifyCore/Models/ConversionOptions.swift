public struct ConversionOptions: Equatable, Sendable {
    public var ocrLanguage: OCRLanguageMode

    public init(ocrLanguage: OCRLanguageMode = .auto) {
        self.ocrLanguage = ocrLanguage
    }

    public static let `default` = ConversionOptions()
}
