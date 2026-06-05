using System.IO;
using MDify.Windows.Models;

namespace MDify.Windows.Support;

public sealed class ConvertibleFilePolicy
{
    public static readonly IReadOnlySet<string> LiteExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".xls",
        ".html",
        ".htm",
        ".csv",
        ".json",
        ".xml",
        ".txt",
        ".md",
        ".zip",
        ".epub"
    };

    public static readonly IReadOnlySet<string> OcrImageExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
        ".bmp"
    };

    public static readonly IReadOnlySet<string> OcrExtensions = new HashSet<string>(
        LiteExtensions.Concat(OcrImageExtensions),
        StringComparer.OrdinalIgnoreCase);

    public static ConvertibleFilePolicy Default { get; } = new(WorkerKind.Ocr);

    private readonly IReadOnlySet<string> _supportedExtensions;

    public ConvertibleFilePolicy(WorkerKind workerKind = WorkerKind.Ocr)
        : this(workerKind == WorkerKind.Lite ? LiteExtensions : OcrExtensions)
    {
    }

    public ConvertibleFilePolicy(IEnumerable<string> supportedExtensions)
    {
        _supportedExtensions = new HashSet<string>(
            supportedExtensions.Select(NormalizeExtension),
            StringComparer.OrdinalIgnoreCase);
    }

    public bool IsConvertibleFile(string path)
    {
        var extension = Path.GetExtension(path);
        return !string.IsNullOrWhiteSpace(extension) && _supportedExtensions.Contains(extension);
    }

    public bool IsLiteSupported(string path) => LiteExtensions.Contains(Path.GetExtension(path));

    public bool IsOcrSupported(string path) => OcrExtensions.Contains(Path.GetExtension(path));

    public bool IsImage(string path) => OcrImageExtensions.Contains(Path.GetExtension(path));

    public bool IsPdf(string path) => string.Equals(Path.GetExtension(path), ".pdf", StringComparison.OrdinalIgnoreCase);

    private static string NormalizeExtension(string extension)
    {
        if (string.IsNullOrWhiteSpace(extension))
        {
            return string.Empty;
        }

        return extension.StartsWith(".", StringComparison.Ordinal) ? extension : $".{extension}";
    }
}
