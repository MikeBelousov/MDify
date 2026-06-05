using System.IO;
using MDify.Windows.Models;

namespace MDify.Windows.Support;

public sealed class OutputFileNamer
{
    public string GetMarkdownPath(
        string inputPath,
        string outputRoot,
        ISet<string>? reservedPaths = null)
    {
        var baseName = Path.GetFileNameWithoutExtension(inputPath);
        return GetUniqueMarkdownPath(outputRoot, baseName, reservedPaths);
    }

    public string GetMarkdownPath(
        ConversionItem item,
        string outputRoot,
        ISet<string>? reservedPaths = null)
    {
        if (string.IsNullOrWhiteSpace(item.SourceRootPath) || string.IsNullOrWhiteSpace(item.RelativeOutputPath))
        {
            return GetMarkdownPath(item.InputPath, outputRoot, reservedPaths);
        }

        var relativeDirectory = Path.GetDirectoryName(item.RelativeOutputPath);
        var targetDirectory = string.IsNullOrWhiteSpace(relativeDirectory)
            ? outputRoot
            : Path.Combine(outputRoot, relativeDirectory);
        var baseName = Path.GetFileNameWithoutExtension(item.RelativeOutputPath);

        return GetUniqueMarkdownPath(targetDirectory, baseName, reservedPaths);
    }

    public string ReserveMarkdownPath(
        string inputPath,
        string outputRoot,
        ISet<string> reservedPaths)
    {
        var path = GetMarkdownPath(inputPath, outputRoot, reservedPaths);
        reservedPaths.Add(path);
        return path;
    }

    public string ReserveMarkdownPath(
        ConversionItem item,
        string outputRoot,
        ISet<string> reservedPaths)
    {
        var path = GetMarkdownPath(item, outputRoot, reservedPaths);
        reservedPaths.Add(path);
        return path;
    }

    private static string GetUniqueMarkdownPath(
        string outputDirectory,
        string baseName,
        ISet<string>? reservedPaths)
    {
        var candidate = Path.Combine(outputDirectory, $"{baseName}.md");
        var suffix = 2;

        while (File.Exists(candidate) || IsReserved(candidate, reservedPaths))
        {
            candidate = Path.Combine(outputDirectory, $"{baseName} {suffix}.md");
            suffix++;
        }

        return candidate;
    }

    private static bool IsReserved(string candidate, ISet<string>? reservedPaths)
    {
        return reservedPaths is not null
            && reservedPaths.Any(reservedPath =>
                string.Equals(reservedPath, candidate, StringComparison.OrdinalIgnoreCase));
    }
}
