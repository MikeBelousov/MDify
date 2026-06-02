import Foundation

public struct OutputRevealPolicy {
    public init() {}

    public func canRevealOutput(for item: ConversionItem) -> Bool {
        guard item.status == .succeeded, let outputURL = item.outputURL else {
            return false
        }

        var isDirectory: ObjCBool = false
        return FileManager.default.fileExists(atPath: outputURL.path, isDirectory: &isDirectory)
            && !isDirectory.boolValue
    }
}
