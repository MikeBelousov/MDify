namespace MDify.Windows.Models;

public sealed record ConversionItem(
    Guid Id,
    string InputPath,
    string? SourceRootPath,
    string? RelativeOutputPath,
    string? OutputPath,
    ConversionStatus Status,
    string MarkdownText,
    string? ErrorMessage,
    string Log)
{
    public ConversionItem(
        string inputPath,
        string? sourceRootPath = null,
        string? relativeOutputPath = null,
        string? outputPath = null,
        ConversionStatus status = ConversionStatus.Pending,
        string markdownText = "",
        string? errorMessage = null,
        string log = "")
        : this(
            Guid.NewGuid(),
            inputPath,
            sourceRootPath,
            relativeOutputPath,
            outputPath,
            status,
            markdownText,
            errorMessage,
            log)
    {
    }

    public string DisplayName => Path.GetFileName(InputPath);

    public string? FolderRelativeDisplayPath => RelativeOutputPath;
}
