using System.IO;
using System.Text.RegularExpressions;
using MDify.Windows.Models;

namespace MDify.Windows.Services;

public sealed class NativeOcrRoutingException : Exception
{
    public NativeOcrRoutingException(string message, Exception? innerException = null)
        : base(message, innerException)
    {
    }
}

public sealed class NativeOcrRoutingClient : IWorkerConverting
{
    private static readonly IReadOnlySet<string> ImageExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp"
    };

    private const int MinimumTextCharacters = 12;
    private const double MinimumAverageConfidence = 0.45;

    private readonly IWorkerConverting _workerClient;
    private readonly IWorkerConverting? _rapidOcrWorkerClient;
    private readonly INativeOcrService _nativeOcr;

    public NativeOcrRoutingClient(
        WorkerKind workerKind,
        IWorkerConverting workerClient,
        IWorkerConverting? rapidOcrWorkerClient = null,
        INativeOcrService? nativeOcr = null)
    {
        WorkerKind = workerKind;
        _workerClient = workerClient;
        _rapidOcrWorkerClient = rapidOcrWorkerClient;
        _nativeOcr = nativeOcr ?? new WindowsNativeOcrService();
    }

    public WorkerKind WorkerKind { get; }

    public async Task<WorkerResponse> ConvertAsync(
        string inputPath,
        string outputPath,
        CancellationToken cancellationToken)
    {
        if (IsImage(inputPath))
        {
            return await ConvertWithNativeOcrAsync(inputPath, outputPath, cancellationToken)
                .ConfigureAwait(false);
        }

        if (IsPdf(inputPath))
        {
            return await ConvertPdfAsync(inputPath, outputPath, cancellationToken)
                .ConfigureAwait(false);
        }

        return await _workerClient.ConvertAsync(inputPath, outputPath, cancellationToken)
            .ConfigureAwait(false);
    }

    private async Task<WorkerResponse> ConvertPdfAsync(
        string inputPath,
        string outputPath,
        CancellationToken cancellationToken)
    {
        var preflightResponse = await _workerClient.ConvertAsync(inputPath, outputPath, cancellationToken)
            .ConfigureAwait(false);
        if (!preflightResponse.Ok)
        {
            return preflightResponse;
        }

        var markdown = File.Exists(outputPath) ? await File.ReadAllTextAsync(outputPath, cancellationToken) : "";
        if (!IsAlmostEmptyText(markdown))
        {
            return preflightResponse;
        }

        return await ConvertWithNativeOcrAsync(inputPath, outputPath, cancellationToken)
            .ConfigureAwait(false);
    }

    private async Task<WorkerResponse> ConvertWithNativeOcrAsync(
        string inputPath,
        string outputPath,
        CancellationToken cancellationToken)
    {
        NativeOcrResult result;
        try
        {
            result = await _nativeOcr.RecognizeAsync(inputPath, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception error) when (error is not OperationCanceledException)
        {
            if (HasRapidOcrFallback)
            {
                return await FallbackToRapidOcrAsync(
                    inputPath,
                    outputPath,
                    "Windows Text Recognizer failed; used RapidOCR fallback.",
                    cancellationToken).ConfigureAwait(false);
            }

            throw new NativeOcrRoutingException(
                "Windows Text Recognizer failed and no RapidOCR fallback worker is bundled.",
                error);
        }

        var quality = MeasureQuality(result.Markdown);
        var isWeak = quality.IsEmpty
            || quality.AlphanumericCount < MinimumTextCharacters
            || result.AverageConfidence < MinimumAverageConfidence;

        if (isWeak && WorkerKind == WorkerKind.Ocr && !HasRapidOcrFallback)
        {
            throw new NativeOcrRoutingException(
                "Windows Text Recognizer was weak and no RapidOCR fallback worker is bundled.");
        }

        if (isWeak && HasRapidOcrFallback)
        {
            return await FallbackToRapidOcrAsync(
                inputPath,
                outputPath,
                "Windows Text Recognizer was weak; used RapidOCR fallback.",
                cancellationToken).ConfigureAwait(false);
        }

        if (quality.IsEmpty)
        {
            throw new NativeOcrRoutingException("Windows Text Recognizer did not recognize any text.");
        }

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
        await File.WriteAllTextAsync(outputPath, result.Markdown, cancellationToken).ConfigureAwait(false);

        var warnings = new List<string>();
        if (isWeak)
        {
            warnings.Add("Windows Text Recognizer confidence was low; saved native result without RapidOCR fallback.");
        }

        return new WorkerResponse(
            true,
            outputPath,
            inputPath,
            "native",
            "windows-text-recognizer",
            true,
            warnings,
            null,
            null);
    }

    private bool HasRapidOcrFallback => WorkerKind == WorkerKind.Ocr && _rapidOcrWorkerClient is not null;

    private async Task<WorkerResponse> FallbackToRapidOcrAsync(
        string inputPath,
        string outputPath,
        string warning,
        CancellationToken cancellationToken)
    {
        if (_rapidOcrWorkerClient is null)
        {
            throw new NativeOcrRoutingException("RapidOCR fallback worker is not bundled.");
        }

        var response = await _rapidOcrWorkerClient.ConvertAsync(inputPath, outputPath, cancellationToken)
            .ConfigureAwait(false);
        return response with { Warnings = response.Warnings.Concat(new[] { warning }).ToArray() };
    }

    private static bool IsImage(string path)
    {
        return ImageExtensions.Contains(Path.GetExtension(path));
    }

    private static bool IsPdf(string path)
    {
        return string.Equals(Path.GetExtension(path), ".pdf", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsAlmostEmptyText(string markdown)
    {
        return MeasureQuality(markdown).AlphanumericCount < MinimumTextCharacters;
    }

    private static TextQuality MeasureQuality(string markdown)
    {
        var alphanumericCount = Regex.Matches(markdown, @"[\p{L}\p{Nd}]").Count;
        return new TextQuality(
            string.IsNullOrWhiteSpace(markdown),
            alphanumericCount);
    }

    private sealed record TextQuality(
        bool IsEmpty,
        int AlphanumericCount);
}
