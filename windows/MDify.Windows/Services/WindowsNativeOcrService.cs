using System.Text;
using MDify.Windows.Models;
using Microsoft.Graphics.Imaging;
using Microsoft.Windows.AI;
using Microsoft.Windows.AI.Imaging;
using Windows.Data.Pdf;
using Windows.Graphics.Imaging;
using Windows.Storage;
using Windows.Storage.Streams;

namespace MDify.Windows.Services;

public sealed class WindowsNativeOcrService : INativeOcrService
{
    private const double PdfRenderDpi = 300.0;
    private const double PdfPointDpi = 72.0;

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

    public async Task<NativeOcrResult> RecognizeAsync(
        string inputPath,
        CancellationToken cancellationToken)
    {
        using var recognizer = await EnsureRecognizerReadyAsync().ConfigureAwait(false);
        var extension = Path.GetExtension(inputPath);
        if (ImageExtensions.Contains(extension))
        {
            using var imageBuffer = await LoadImageBufferFromFileAsync(inputPath).ConfigureAwait(false);
            return RecognizeImageBuffer(recognizer, imageBuffer);
        }

        if (string.Equals(extension, ".pdf", StringComparison.OrdinalIgnoreCase))
        {
            return await RecognizePdfAsync(recognizer, inputPath, cancellationToken).ConfigureAwait(false);
        }

        throw new NotSupportedException($"Windows Text Recognizer does not support {extension} input.");
    }

    private static async Task<TextRecognizer> EnsureRecognizerReadyAsync()
    {
        var readyState = TextRecognizer.GetReadyState();
        if (readyState == AIFeatureReadyState.CapabilityMissing)
        {
            throw new InvalidOperationException(
                "Windows Text Recognizer requires the systemAIModels capability in the app package manifest.");
        }

        if (readyState == AIFeatureReadyState.NotReady)
        {
            var loadResult = await TextRecognizer.EnsureReadyAsync();
            if (loadResult.Status != AIFeatureReadyResultState.Success)
            {
                throw new InvalidOperationException("Windows Text Recognizer model preparation failed.");
            }
        }
        else if (readyState != AIFeatureReadyState.Ready)
        {
            throw new InvalidOperationException($"Windows Text Recognizer is not ready: {readyState}.");
        }

        return await TextRecognizer.CreateAsync();
    }

    private static async Task<ImageBuffer> LoadImageBufferFromFileAsync(string filePath)
    {
        var file = await StorageFile.GetFileFromPathAsync(filePath);
        using var stream = await file.OpenAsync(FileAccessMode.Read);
        var decoder = await BitmapDecoder.CreateAsync(stream);
        var bitmap = await decoder.GetSoftwareBitmapAsync();
        if (bitmap is null)
        {
            throw new InvalidOperationException("Failed to decode image for Windows Text Recognizer.");
        }

        return ImageBuffer.CreateForSoftwareBitmap(bitmap);
    }

    private static async Task<NativeOcrResult> RecognizePdfAsync(
        TextRecognizer recognizer,
        string inputPath,
        CancellationToken cancellationToken)
    {
        var file = await StorageFile.GetFileFromPathAsync(inputPath);
        using var stream = await file.OpenAsync(FileAccessMode.Read);
        var document = await PdfDocument.LoadFromStreamAsync(stream);
        var pageResults = new List<NativeOcrResult>();

        for (uint index = 0; index < document.PageCount; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var page = document.GetPage(index);
            using var pageStream = new InMemoryRandomAccessStream();
            var renderOptions = new PdfPageRenderOptions
            {
                DestinationWidth = (uint)Math.Ceiling(page.Size.Width * PdfRenderDpi / PdfPointDpi),
                DestinationHeight = (uint)Math.Ceiling(page.Size.Height * PdfRenderDpi / PdfPointDpi)
            };
            await page.RenderToStreamAsync(pageStream, renderOptions);
            pageStream.Seek(0);

            var decoder = await BitmapDecoder.CreateAsync(pageStream);
            var bitmap = await decoder.GetSoftwareBitmapAsync();
            if (bitmap is null)
            {
                continue;
            }

            using var imageBuffer = ImageBuffer.CreateForSoftwareBitmap(bitmap);
            pageResults.Add(RecognizeImageBuffer(recognizer, imageBuffer));
        }

        return MergePageResults(pageResults);
    }

    private static NativeOcrResult RecognizeImageBuffer(
        TextRecognizer recognizer,
        ImageBuffer imageBuffer)
    {
        var recognizedText = recognizer.RecognizeTextFromImage(imageBuffer);
        var markdown = new StringBuilder();
        var confidences = new List<double>();

        foreach (var line in recognizedText.Lines)
        {
            if (!string.IsNullOrWhiteSpace(line.Text))
            {
                markdown.AppendLine(line.Text);
            }

            foreach (var word in line.Words)
            {
                confidences.Add(word.MatchConfidence);
            }
        }

        var averageConfidence = confidences.Count == 0 ? 0 : confidences.Average();
        return new NativeOcrResult(markdown.ToString(), averageConfidence);
    }

    private static NativeOcrResult MergePageResults(IReadOnlyList<NativeOcrResult> pageResults)
    {
        if (pageResults.Count == 0)
        {
            return new NativeOcrResult("", 0);
        }

        var markdown = string.Join(
            Environment.NewLine + Environment.NewLine,
            pageResults.Select(result => result.Markdown.Trim()).Where(text => text.Length > 0));
        var confidenceValues = pageResults
            .Where(result => result.AverageConfidence > 0)
            .Select(result => result.AverageConfidence)
            .ToArray();
        var averageConfidence = confidenceValues.Length == 0 ? 0 : confidenceValues.Average();
        return new NativeOcrResult(markdown, averageConfidence);
    }
}
