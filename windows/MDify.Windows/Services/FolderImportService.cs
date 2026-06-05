using System.IO;
using MDify.Windows.Support;

namespace MDify.Windows.Services;

public enum FolderScanMode
{
    TopLevelOnly,
    Recursive
}

public sealed record FolderScannedFile(
    string Path,
    string RelativePath);

public sealed record FolderScanResult(
    string RootPath,
    IReadOnlyList<FolderScannedFile> Files,
    int SkippedUnsupportedCount,
    bool HasSubfolders);

public sealed class FolderImportService
{
    private readonly ConvertibleFilePolicy _policy;

    public FolderImportService(ConvertibleFilePolicy? policy = null)
    {
        _policy = policy ?? ConvertibleFilePolicy.Default;
    }

    public FolderScanResult Scan(string rootPath, FolderScanMode mode)
    {
        if (!Directory.Exists(rootPath))
        {
            return new FolderScanResult(rootPath, Array.Empty<FolderScannedFile>(), 0, false);
        }

        var files = new List<FolderScannedFile>();
        var skippedUnsupportedCount = 0;
        var hasSubfolders = false;

        Visit(rootPath, relativePrefix: "");

        return new FolderScanResult(rootPath, files, skippedUnsupportedCount, hasSubfolders);

        void Visit(string directory, string relativePrefix)
        {
            foreach (var child in EnumerateFileSystemEntries(directory))
            {
                var name = System.IO.Path.GetFileName(child);
                if (ShouldSkipName(name))
                {
                    skippedUnsupportedCount++;
                    continue;
                }

                var attributes = File.GetAttributes(child);
                if (attributes.HasFlag(FileAttributes.Hidden) || attributes.HasFlag(FileAttributes.ReparsePoint))
                {
                    skippedUnsupportedCount++;
                    continue;
                }

                if (attributes.HasFlag(FileAttributes.Directory))
                {
                    hasSubfolders = true;
                    if (IsSkippedDirectoryPackage(child))
                    {
                        skippedUnsupportedCount++;
                        continue;
                    }

                    if (mode == FolderScanMode.Recursive)
                    {
                        var nextPrefix = string.IsNullOrEmpty(relativePrefix)
                            ? name
                            : System.IO.Path.Combine(relativePrefix, name);
                        Visit(child, nextPrefix);
                    }

                    continue;
                }

                if (!_policy.IsConvertibleFile(child))
                {
                    skippedUnsupportedCount++;
                    continue;
                }

                var relativePath = string.IsNullOrEmpty(relativePrefix)
                    ? name
                    : System.IO.Path.Combine(relativePrefix, name);
                files.Add(new FolderScannedFile(child, relativePath));
            }
        }
    }

    private static IEnumerable<string> EnumerateFileSystemEntries(string directory)
    {
        return Directory.EnumerateFileSystemEntries(directory)
            .OrderBy(entry => entry, StringComparer.OrdinalIgnoreCase);
    }

    private static bool ShouldSkipName(string name)
    {
        return name.StartsWith(".", StringComparison.Ordinal)
            || string.Equals(name, "Thumbs.db", StringComparison.OrdinalIgnoreCase)
            || string.Equals(name, "desktop.ini", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsSkippedDirectoryPackage(string path)
    {
        var extension = System.IO.Path.GetExtension(path);
        return string.Equals(extension, ".app", StringComparison.OrdinalIgnoreCase)
            || string.Equals(extension, ".bundle", StringComparison.OrdinalIgnoreCase);
    }
}
