import CoreGraphics
import Foundation
import ImageIO
import Vision

public struct NativeOCRResult: Equatable, Sendable {
    public let markdown: String
    public let averageConfidence: Double

    public init(markdown: String, averageConfidence: Double) {
        self.markdown = markdown
        self.averageConfidence = averageConfidence
    }
}

public protocol NativeOCRRecognizing: Sendable {
    func recognize(inputURL: URL) async throws -> NativeOCRResult
}

public enum VisionOCRServiceError: LocalizedError, Equatable {
    case unsupportedFile(String)
    case unreadableImage(String)
    case unreadablePDF(String)
    case failedToRenderPDFPage(Int)

    public var errorDescription: String? {
        switch self {
        case .unsupportedFile(let ext):
            "Apple Vision OCR does not support .\(ext) files."
        case .unreadableImage(let path):
            "Could not read image for Apple Vision OCR: \(path)"
        case .unreadablePDF(let path):
            "Could not read PDF for Apple Vision OCR: \(path)"
        case .failedToRenderPDFPage(let page):
            "Could not render PDF page \(page) for Apple Vision OCR."
        }
    }
}

public struct VisionOCRService: NativeOCRRecognizing {
    private static let preferredLanguages = ["ru-RU", "en-US"]
    private static let imageExtensions: Set<String> = ["jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"]
    private static let pdfRenderScale: CGFloat = 300.0 / 72.0

    public init() {}

    public func recognize(inputURL: URL) async throws -> NativeOCRResult {
        try await Task.detached(priority: .userInitiated) {
            try Self.recognizeSync(inputURL: inputURL)
        }.value
    }

    private static func recognizeSync(inputURL: URL) throws -> NativeOCRResult {
        let ext = inputURL.pathExtension.lowercased()
        if imageExtensions.contains(ext) {
            return try recognizeImage(at: inputURL)
        }
        if ext == "pdf" {
            return try recognizePDF(at: inputURL)
        }
        throw VisionOCRServiceError.unsupportedFile(ext)
    }

    private static func recognizeImage(at url: URL) throws -> NativeOCRResult {
        guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw VisionOCRServiceError.unreadableImage(url.path)
        }

        let orientation = imageOrientation(from: source, index: 0)
        return try recognize(cgImage: image, orientation: orientation)
    }

    private static func recognizePDF(at url: URL) throws -> NativeOCRResult {
        guard let document = CGPDFDocument(url as CFURL) else {
            throw VisionOCRServiceError.unreadablePDF(url.path)
        }
        guard document.numberOfPages > 0 else {
            return NativeOCRResult(markdown: "", averageConfidence: 0)
        }

        var pageMarkdown: [String] = []
        var confidences: [Double] = []

        for pageNumber in 1...document.numberOfPages {
            guard let page = document.page(at: pageNumber),
                  let image = render(page: page) else {
                throw VisionOCRServiceError.failedToRenderPDFPage(pageNumber)
            }
            let result = try recognize(cgImage: image, orientation: .up)
            let trimmed = result.markdown.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                pageMarkdown.append(trimmed)
            }
            if result.averageConfidence > 0 {
                confidences.append(result.averageConfidence)
            }
        }

        let markdown = pageMarkdown.joined(separator: "\n\n")
        return NativeOCRResult(
            markdown: markdown.isEmpty ? "" : markdown + "\n",
            averageConfidence: average(confidences)
        )
    }

    private static func recognize(cgImage: CGImage, orientation: CGImagePropertyOrientation) throws -> NativeOCRResult {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        request.revision = VNRecognizeTextRequestRevision3

        let supportedLanguages = Set((try? request.supportedRecognitionLanguages()) ?? [])
        let recognitionLanguages = preferredLanguages.filter { supportedLanguages.contains($0) }
        if recognitionLanguages.isEmpty {
            request.automaticallyDetectsLanguage = true
        } else {
            request.recognitionLanguages = recognitionLanguages
        }

        let handler = VNImageRequestHandler(cgImage: cgImage, orientation: orientation, options: [:])
        try handler.perform([request])

        let lines = (request.results ?? [])
            .compactMap { observation -> RecognizedLine? in
                guard let candidate = observation.topCandidates(1).first else { return nil }
                let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !text.isEmpty else { return nil }
                return RecognizedLine(
                    text: text,
                    boundingBox: observation.boundingBox,
                    confidence: Double(candidate.confidence)
                )
            }
            .sorted(by: readingOrder)

        let markdown = lines.map(\.text).joined(separator: "\n")
        return NativeOCRResult(
            markdown: markdown.isEmpty ? "" : markdown + "\n",
            averageConfidence: average(lines.map(\.confidence))
        )
    }

    private static func render(page: CGPDFPage) -> CGImage? {
        let cropBox = page.getBoxRect(.cropBox)
        let mediaBox = page.getBoxRect(.mediaBox)
        let box = cropBox.isEmpty ? mediaBox : cropBox
        guard box.width > 0, box.height > 0 else { return nil }

        let width = max(1, Int((box.width * pdfRenderScale).rounded(.up)))
        let height = max(1, Int((box.height * pdfRenderScale).rounded(.up)))
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else {
            return nil
        }

        context.setFillColor(CGColor(gray: 1, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        context.saveGState()
        context.scaleBy(x: pdfRenderScale, y: pdfRenderScale)
        context.translateBy(x: -box.origin.x, y: -box.origin.y)
        context.drawPDFPage(page)
        context.restoreGState()
        return context.makeImage()
    }

    private static func imageOrientation(from source: CGImageSource, index: Int) -> CGImagePropertyOrientation {
        let properties = CGImageSourceCopyPropertiesAtIndex(source, index, nil) as? [CFString: Any]
        let rawOrientation = properties?[kCGImagePropertyOrientation] as? UInt32
        return rawOrientation.flatMap(CGImagePropertyOrientation.init(rawValue:)) ?? .up
    }

    private static func readingOrder(_ lhs: RecognizedLine, _ rhs: RecognizedLine) -> Bool {
        let verticalDistance = abs(lhs.boundingBox.midY - rhs.boundingBox.midY)
        if verticalDistance > 0.02 {
            return lhs.boundingBox.midY > rhs.boundingBox.midY
        }
        return lhs.boundingBox.minX < rhs.boundingBox.minX
    }

    private static func average(_ values: [Double]) -> Double {
        guard !values.isEmpty else { return 0 }
        return values.reduce(0, +) / Double(values.count)
    }
}

private struct RecognizedLine {
    let text: String
    let boundingBox: CGRect
    let confidence: Double
}
