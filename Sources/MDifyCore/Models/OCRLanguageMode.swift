public enum OCRLanguageMode: String, CaseIterable, Sendable {
    case auto
    case cyrillic
    case latin

    public var displayName: String {
        switch self {
        case .auto: "Automatic"
        case .cyrillic: "Cyrillic"
        case .latin: "Latin"
        }
    }
}
