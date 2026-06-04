import Foundation

public struct ConvertibleFilePolicy: Sendable {
    public static let `default` = ConvertibleFilePolicy()

    public let supportedExtensions: Set<String>

    public init(supportedExtensions: Set<String> = ConvertibleFilePolicy.defaultExtensions) {
        self.supportedExtensions = Set(supportedExtensions.map { $0.lowercased() })
    }

    public init(workerKind: WorkerKind) {
        switch workerKind {
        case .lite:
            self.init(supportedExtensions: Self.liteExtensions)
        case .ocr:
            self.init(supportedExtensions: Self.ocrExtensions)
        }
    }

    public func isConvertibleFile(_ url: URL) -> Bool {
        let ext = url.pathExtension.lowercased()
        return !ext.isEmpty && supportedExtensions.contains(ext)
    }

    public static let liteExtensions: Set<String> = [
        "pdf",
        "docx", "pptx", "xlsx", "xls",
        "html", "htm", "csv", "json", "xml", "txt", "md",
        "epub", "zip",
        "jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"
    ]

    public static let ocrExtensions: Set<String> = liteExtensions

    public static let defaultExtensions: Set<String> = ocrExtensions
}
