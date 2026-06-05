using MDify.Windows.Models;
using MDify.Windows.Services;

namespace MDify.Windows.Tests;

public sealed class NativeOcrRoutingClientTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"mdify-routing-{Guid.NewGuid():N}");

    public NativeOcrRoutingClientTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public async Task Image_UsesNativeOcrFirst()
    {
        var input = Touch("scan.png");
        var output = Path.Combine(_root, "scan.md");
        var worker = new SpyWorker("worker text");
        var native = new StubNativeOcr(new NativeOcrResult("Native recognized text", 0.9));
        var client = new NativeOcrRoutingClient(WorkerKind.Lite, worker, nativeOcr: native);

        var response = await client.ConvertAsync(input, output, CancellationToken.None);

        Assert.Equal("native", response.Worker);
        Assert.Equal("windows-text-recognizer", response.Engine);
        Assert.True(response.OcrUsed);
        Assert.Equal("Native recognized text", File.ReadAllText(output));
        Assert.Equal(1, native.InvocationCount);
        Assert.Equal(0, worker.InvocationCount);
    }

    [Fact]
    public async Task Pdf_WithEnoughPreflightText_SkipsNativeOcr()
    {
        var input = Touch("text.pdf");
        var output = Path.Combine(_root, "text.md");
        var worker = new SpyWorker("This PDF already has extractable text.");
        var native = new StubNativeOcr(new NativeOcrResult("Native should not run", 0.9));
        var client = new NativeOcrRoutingClient(WorkerKind.Ocr, worker, nativeOcr: native);

        var response = await client.ConvertAsync(input, output, CancellationToken.None);

        Assert.Equal("ocr", response.Worker);
        Assert.Equal("markitdown", response.Engine);
        Assert.False(response.OcrUsed);
        Assert.Equal(1, worker.InvocationCount);
        Assert.Equal(0, native.InvocationCount);
    }

    [Fact]
    public async Task Pdf_WithAlmostEmptyPreflight_RunsNativeOcr()
    {
        var input = Touch("scan.pdf");
        var output = Path.Combine(_root, "scan.md");
        var worker = new SpyWorker("");
        var native = new StubNativeOcr(new NativeOcrResult("Native PDF text", 0.9));
        var client = new NativeOcrRoutingClient(WorkerKind.Ocr, worker, nativeOcr: native);

        var response = await client.ConvertAsync(input, output, CancellationToken.None);

        Assert.Equal("native", response.Worker);
        Assert.Equal("Native PDF text", File.ReadAllText(output));
        Assert.Equal(1, worker.InvocationCount);
        Assert.Equal(1, native.InvocationCount);
    }

    [Fact]
    public async Task WeakNativeOcr_FallsBackToRapidOcrWorker()
    {
        var input = Touch("scan.jpg");
        var output = Path.Combine(_root, "scan.md");
        var preflight = new SpyWorker("preflight text");
        var fallback = new SpyWorker("# RapidOCR", engine: "rapidocr", ocrUsed: true);
        var native = new StubNativeOcr(new NativeOcrResult("bad", 0.2));
        var client = new NativeOcrRoutingClient(WorkerKind.Ocr, preflight, fallback, native);

        var response = await client.ConvertAsync(input, output, CancellationToken.None);

        Assert.Equal("rapidocr", response.Engine);
        Assert.Contains(response.Warnings, warning => warning.Contains("weak", StringComparison.OrdinalIgnoreCase));
        Assert.Equal("# RapidOCR", File.ReadAllText(output));
        Assert.Equal(0, preflight.InvocationCount);
        Assert.Equal(1, fallback.InvocationCount);
    }

    [Fact]
    public async Task WeakNativeOcr_IsClearErrorWhenRapidOcrFallbackMissing()
    {
        var input = Touch("scan.jpg");
        var output = Path.Combine(_root, "scan.md");
        var preflight = new SpyWorker("preflight text");
        var native = new StubNativeOcr(new NativeOcrResult("bad", 0.2));
        var client = new NativeOcrRoutingClient(WorkerKind.Ocr, preflight, nativeOcr: native);

        var error = await Assert.ThrowsAsync<NativeOcrRoutingException>(() =>
            client.ConvertAsync(input, output, CancellationToken.None));

        Assert.Contains("RapidOCR fallback", error.Message, StringComparison.OrdinalIgnoreCase);
        Assert.Equal(0, preflight.InvocationCount);
    }

    [Fact]
    public async Task NativeFailure_FallsBackToRapidOcrWhenAvailable()
    {
        var input = Touch("scan.png");
        var output = Path.Combine(_root, "scan.md");
        var fallback = new SpyWorker("# RapidOCR", engine: "rapidocr", ocrUsed: true);
        var native = new ThrowingNativeOcr();
        var client = new NativeOcrRoutingClient(WorkerKind.Ocr, new SpyWorker(""), fallback, native);

        var response = await client.ConvertAsync(input, output, CancellationToken.None);

        Assert.Equal("rapidocr", response.Engine);
        Assert.Contains(response.Warnings, warning => warning.Contains("failed", StringComparison.OrdinalIgnoreCase));
    }

    [Fact]
    public async Task NativeFailure_IsClearErrorWithoutRapidOcrFallback()
    {
        var input = Touch("scan.png");
        var output = Path.Combine(_root, "scan.md");
        var client = new NativeOcrRoutingClient(
            WorkerKind.Lite,
            new SpyWorker(""),
            nativeOcr: new ThrowingNativeOcr());

        var error = await Assert.ThrowsAsync<NativeOcrRoutingException>(() =>
            client.ConvertAsync(input, output, CancellationToken.None));

        Assert.Contains("Windows Text Recognizer", error.Message, StringComparison.OrdinalIgnoreCase);
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    private string Touch(string fileName)
    {
        var path = Path.Combine(_root, fileName);
        File.WriteAllText(path, "");
        return path;
    }

    private sealed class StubNativeOcr : INativeOcrService
    {
        private readonly NativeOcrResult _result;

        public StubNativeOcr(NativeOcrResult result)
        {
            _result = result;
        }

        public int InvocationCount { get; private set; }

        public Task<NativeOcrResult> RecognizeAsync(string inputPath, CancellationToken cancellationToken)
        {
            InvocationCount++;
            return Task.FromResult(_result);
        }
    }

    private sealed class ThrowingNativeOcr : INativeOcrService
    {
        public Task<NativeOcrResult> RecognizeAsync(string inputPath, CancellationToken cancellationToken)
        {
            throw new InvalidOperationException("model unavailable");
        }
    }

    private sealed class SpyWorker : IWorkerConverting
    {
        private readonly string _markdown;
        private readonly string _engine;
        private readonly bool _ocrUsed;

        public SpyWorker(string markdown, string engine = "markitdown", bool ocrUsed = false)
        {
            _markdown = markdown;
            _engine = engine;
            _ocrUsed = ocrUsed;
        }

        public WorkerKind WorkerKind => WorkerKind.Ocr;

        public int InvocationCount { get; private set; }

        public Task<WorkerResponse> ConvertAsync(
            string inputPath,
            string outputPath,
            CancellationToken cancellationToken)
        {
            InvocationCount++;
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
            File.WriteAllText(outputPath, _markdown);
            return Task.FromResult(new WorkerResponse(
                true,
                outputPath,
                inputPath,
                "ocr",
                _engine,
                _ocrUsed,
                Array.Empty<string>(),
                null,
                null));
        }
    }
}
