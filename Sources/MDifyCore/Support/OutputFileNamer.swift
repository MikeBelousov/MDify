import Foundation

public struct OutputFileNamer: Sendable {
    public init() {}

    public func markdownURL(for inputURL: URL, in outputDirectory: URL, reserved: Set<String> = []) -> URL {
        let baseName = inputURL.deletingPathExtension().lastPathComponent
        var candidateName = "\(baseName).md"
        var index = 1

        while FileManager.default.fileExists(atPath: outputDirectory.appendingPathComponent(candidateName).path)
            || reserved.contains(candidateName) {
            candidateName = "\(baseName)-\(index).md"
            index += 1
        }

        return outputDirectory.appendingPathComponent(candidateName)
    }

    public func markdownURL(for item: ConversionItem, in outputDirectory: URL, reservedRoots: inout [String: URL]) -> URL {
        guard let sourceRootURL = item.sourceRootURL,
              let relativeOutputPath = item.relativeOutputPath else {
            return markdownURL(for: item.inputURL, in: outputDirectory)
        }

        let sourceRootName = sourceRootURL.lastPathComponent
        let rootOutputDirectory: URL
        if let existing = reservedRoots[sourceRootURL.path] {
            rootOutputDirectory = existing
        } else {
            rootOutputDirectory = uniqueDirectory(named: sourceRootName, in: outputDirectory)
            reservedRoots[sourceRootURL.path] = rootOutputDirectory
        }

        let nsRelativePath = relativeOutputPath as NSString
        let relativeDirectory = nsRelativePath.deletingLastPathComponent
        let outputDirectoryForFile: URL
        if relativeDirectory.isEmpty || relativeDirectory == "." {
            outputDirectoryForFile = rootOutputDirectory
        } else {
            outputDirectoryForFile = relativeDirectory
                .split(separator: "/")
                .reduce(rootOutputDirectory) { partial, component in
                    partial.appendingPathComponent(String(component), isDirectory: true)
                }
        }

        let outputStem = (nsRelativePath.lastPathComponent as NSString).deletingPathExtension
        let outputFileName = "\(outputStem).md"
        return outputDirectoryForFile.appendingPathComponent(outputFileName)
    }

    private func uniqueDirectory(named baseName: String, in outputDirectory: URL) -> URL {
        var candidateName = baseName
        var index = 1

        while FileManager.default.fileExists(atPath: outputDirectory.appendingPathComponent(candidateName).path) {
            candidateName = "\(baseName)-\(index)"
            index += 1
        }

        return outputDirectory.appendingPathComponent(candidateName, isDirectory: true)
    }
}
