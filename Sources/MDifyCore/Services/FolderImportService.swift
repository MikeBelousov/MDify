import Foundation

public enum FolderScanMode: Equatable, Sendable {
    case topLevelOnly
    case recursive
}

public struct FolderImportService {
    private let fileManager: FileManager
    private let policy: ConvertibleFilePolicy

    public init(fileManager: FileManager = .default, policy: ConvertibleFilePolicy = .default) {
        self.fileManager = fileManager
        self.policy = policy
    }

    public func scan(root: URL, mode: FolderScanMode) throws -> FolderScanResult {
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: root.path, isDirectory: &isDirectory), isDirectory.boolValue else {
            return FolderScanResult(rootURL: root, files: [], skippedUnsupportedCount: 0, hasSubfolders: false)
        }

        var files: [FolderScannedFile] = []
        var skippedUnsupportedCount = 0
        var hasSubfolders = false

        func visit(directory: URL, relativePrefix: String) throws {
            let children = try fileManager.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: [.isDirectoryKey, .isRegularFileKey, .isSymbolicLinkKey, .isPackageKey],
                options: [.skipsHiddenFiles]
            )

            for child in children.sorted(by: { $0.path.localizedStandardCompare($1.path) == .orderedAscending }) {
                let name = child.lastPathComponent
                guard !isSystemEntry(name) else {
                    skippedUnsupportedCount += 1
                    continue
                }

                let values = try child.resourceValues(forKeys: [.isDirectoryKey, .isRegularFileKey, .isSymbolicLinkKey, .isPackageKey])
                if values.isSymbolicLink == true {
                    skippedUnsupportedCount += 1
                    continue
                }

                if values.isDirectory == true {
                    hasSubfolders = true
                    if values.isPackage == true || isDirectoryPackage(child) {
                        skippedUnsupportedCount += 1
                        continue
                    }
                    if mode == .recursive {
                        let nextPrefix = relativePrefix.isEmpty ? name : "\(relativePrefix)/\(name)"
                        try visit(directory: child, relativePrefix: nextPrefix)
                    }
                    continue
                }

                guard values.isRegularFile == true else {
                    skippedUnsupportedCount += 1
                    continue
                }

                guard policy.isConvertibleFile(child) else {
                    skippedUnsupportedCount += 1
                    continue
                }

                let relativePath = relativePrefix.isEmpty ? name : "\(relativePrefix)/\(name)"
                files.append(FolderScannedFile(url: child, relativePath: relativePath))
            }
        }

        try visit(directory: root, relativePrefix: "")
        return FolderScanResult(
            rootURL: root,
            files: files,
            skippedUnsupportedCount: skippedUnsupportedCount,
            hasSubfolders: hasSubfolders
        )
    }

    private func isSystemEntry(_ name: String) -> Bool {
        name == ".DS_Store" || name.hasPrefix("._")
    }

    private func isDirectoryPackage(_ url: URL) -> Bool {
        ["app", "framework", "bundle", "plugin", "appex", "xcodeproj", "xcworkspace"]
            .contains(url.pathExtension.lowercased())
    }
}
