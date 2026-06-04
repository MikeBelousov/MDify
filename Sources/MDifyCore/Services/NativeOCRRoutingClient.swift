import Foundation

public enum NativeOCRRoutingError: LocalizedError, Equatable {
    case nativeOCRReturnedNoText

    public var errorDescription: String? {
        switch self {
        case .nativeOCRReturnedNoText:
            "Apple Vision OCR did not recognize any text. Try MDify OCR for RapidOCR fallback."
        }
    }
}

public struct NativeOCRRoutingClient: WorkerConverting {
    private static let imageExtensions: Set<String> = ["jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"]
    private static let minimumTextCharacters = 12
    private static let minimumAverageConfidence = 0.45

    public let workerKind: WorkerKind
    private let workerClient: any WorkerConverting
    private let rapidOCRWorkerClient: (any WorkerConverting)?
    private let nativeOCR: any NativeOCRRecognizing

    public init(
        workerKind: WorkerKind,
        workerClient: any WorkerConverting,
        rapidOCRWorkerClient: (any WorkerConverting)? = nil,
        nativeOCR: any NativeOCRRecognizing = VisionOCRService()
    ) {
        self.workerKind = workerKind
        self.workerClient = workerClient
        self.rapidOCRWorkerClient = rapidOCRWorkerClient
        self.nativeOCR = nativeOCR
    }

    public func convert(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        if Self.isImage(inputURL) {
            return try await convertWithNativeOCR(inputURL: inputURL, outputURL: outputURL)
        }

        if Self.isPDF(inputURL) {
            return try await convertPDF(inputURL: inputURL, outputURL: outputURL)
        }

        return try await workerClient.convert(inputURL: inputURL, outputURL: outputURL)
    }

    private func convertPDF(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        let preflightResponse = try await workerClient.convert(inputURL: inputURL, outputURL: outputURL)
        guard preflightResponse.ok else { return preflightResponse }

        let markdown = (try? String(contentsOf: outputURL, encoding: .utf8)) ?? ""
        guard Self.isAlmostEmptyText(markdown) else {
            return preflightResponse
        }

        return try await convertWithNativeOCR(inputURL: inputURL, outputURL: outputURL)
    }

    private func convertWithNativeOCR(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        let result = try await nativeOCR.recognize(inputURL: inputURL)
        let quality = Self.quality(for: result.markdown)
        let isWeak = quality.isEmpty
            || quality.alphanumericCount < Self.minimumTextCharacters
            || result.averageConfidence < Self.minimumAverageConfidence

        if workerKind == .ocr, isWeak {
            return try await fallbackToRapidOCR(inputURL: inputURL, outputURL: outputURL)
        }

        guard !quality.isEmpty else {
            throw NativeOCRRoutingError.nativeOCRReturnedNoText
        }

        try writeNativeMarkdown(result.markdown, to: outputURL)
        var warnings: [String] = []
        if isWeak {
            warnings.append("Apple Vision OCR confidence was low; saved the native result without RapidOCR fallback.")
        }
        return WorkerResponse(
            ok: true,
            outputPath: outputURL.path,
            inputPath: inputURL.path,
            worker: "native",
            engine: "apple-vision",
            ocrUsed: true,
            warnings: warnings,
            errorCode: nil,
            message: nil
        )
    }

    private func fallbackToRapidOCR(inputURL: URL, outputURL: URL) async throws -> WorkerResponse {
        let fallbackClient = rapidOCRWorkerClient ?? workerClient
        let response = try await fallbackClient.convert(inputURL: inputURL, outputURL: outputURL)
        return response.appendingWarning("Apple Vision OCR was weak; used RapidOCR fallback.")
    }

    private func writeNativeMarkdown(_ markdown: String, to outputURL: URL) throws {
        try FileManager.default.createDirectory(
            at: outputURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try markdown.write(to: outputURL, atomically: true, encoding: .utf8)
    }

    private static func isImage(_ url: URL) -> Bool {
        imageExtensions.contains(url.pathExtension.lowercased())
    }

    private static func isPDF(_ url: URL) -> Bool {
        url.pathExtension.lowercased() == "pdf"
    }

    private static func isAlmostEmptyText(_ markdown: String) -> Bool {
        quality(for: markdown).alphanumericCount < minimumTextCharacters
    }

    private static func quality(for markdown: String) -> TextQuality {
        let alphanumericCount = markdown.unicodeScalars.filter {
            CharacterSet.alphanumerics.contains($0)
        }.count
        return TextQuality(
            isEmpty: markdown.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
            alphanumericCount: alphanumericCount
        )
    }
}

private struct TextQuality {
    let isEmpty: Bool
    let alphanumericCount: Int
}

private extension WorkerResponse {
    func appendingWarning(_ warning: String) -> WorkerResponse {
        WorkerResponse(
            ok: ok,
            outputPath: outputPath,
            inputPath: inputPath,
            worker: worker,
            engine: engine,
            ocrUsed: ocrUsed,
            warnings: warnings + [warning],
            errorCode: errorCode,
            message: message
        )
    }
}
