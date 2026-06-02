import Foundation

public struct ConvertibleFilePolicy: Sendable {
    public static let `default` = ConvertibleFilePolicy()

    public let supportedExtensions: Set<String>

    public init(supportedExtensions: Set<String> = ConvertibleFilePolicy.defaultExtensions) {
        self.supportedExtensions = Set(supportedExtensions.map { $0.lowercased() })
    }

    public func isConvertibleFile(_ url: URL) -> Bool {
        let ext = url.pathExtension.lowercased()
        return !ext.isEmpty && supportedExtensions.contains(ext)
    }

    public static let defaultExtensions: Set<String> = [
        "pdf",
        "docx", "doc", "pptx", "xlsx", "xls",
        "html", "htm", "csv", "json", "xml", "txt", "md", "rtf",
        "epub", "ipynb", "zip", "msg",
        "jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp",
        "wav", "mp3", "m4a", "mp4", "mov"
    ]
}
