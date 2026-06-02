import Foundation

public struct ConversionItem: Identifiable, Equatable, Sendable {
    public let id: UUID
    public let inputURL: URL
    public var sourceRootURL: URL?
    public var relativeOutputPath: String?
    public var outputURL: URL?
    public var status: ConversionStatus
    public var markdownText: String
    public var errorMessage: String?
    public var log: String

    public init(
        id: UUID = UUID(),
        inputURL: URL,
        sourceRootURL: URL? = nil,
        relativeOutputPath: String? = nil,
        outputURL: URL? = nil,
        status: ConversionStatus = .pending,
        markdownText: String = "",
        errorMessage: String? = nil,
        log: String = ""
    ) {
        self.id = id
        self.inputURL = inputURL
        self.sourceRootURL = sourceRootURL
        self.relativeOutputPath = relativeOutputPath
        self.outputURL = outputURL
        self.status = status
        self.markdownText = markdownText
        self.errorMessage = errorMessage
        self.log = log
    }

    public var displayName: String {
        inputURL.lastPathComponent
    }

    public var folderRelativeDisplayPath: String? {
        relativeOutputPath
    }
}
