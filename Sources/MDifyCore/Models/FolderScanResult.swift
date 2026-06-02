import Foundation

public struct FolderScannedFile: Equatable, Sendable {
    public let url: URL
    public let relativePath: String

    public init(url: URL, relativePath: String) {
        self.url = url
        self.relativePath = relativePath
    }
}

public struct FolderScanResult: Equatable, Sendable {
    public let rootURL: URL
    public let files: [FolderScannedFile]
    public let skippedUnsupportedCount: Int
    public let hasSubfolders: Bool

    public init(
        rootURL: URL,
        files: [FolderScannedFile],
        skippedUnsupportedCount: Int,
        hasSubfolders: Bool
    ) {
        self.rootURL = rootURL
        self.files = files
        self.skippedUnsupportedCount = skippedUnsupportedCount
        self.hasSubfolders = hasSubfolders
    }
}

public struct FolderImportSummary: Equatable, Sendable {
    public let addedCount: Int
    public let skippedUnsupportedCount: Int
    public let skippedDuplicateCount: Int

    public init(addedCount: Int, skippedUnsupportedCount: Int, skippedDuplicateCount: Int) {
        self.addedCount = addedCount
        self.skippedUnsupportedCount = skippedUnsupportedCount
        self.skippedDuplicateCount = skippedDuplicateCount
    }

    public var displayText: String {
        "Added \(addedCount) files, skipped \(skippedUnsupportedCount) unsupported"
    }
}
