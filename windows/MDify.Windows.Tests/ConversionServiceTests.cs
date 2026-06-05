using System.IO;
using MDify.Windows.Models;
using MDify.Windows.Services;

namespace MDify.Windows.Tests;

public sealed class ConversionServiceTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"mdify-conversion-{Guid.NewGuid():N}");

    public ConversionServiceTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public async Task ConvertAll_ProcessesPendingAndFailedItemsSequentially()
    {
        var first = Touch("first.txt");
        var second = Touch("second.pdf");
        var worker = new QueueWorker();
        var service = new ConversionService(worker);
        service.Items.Add(new ConversionItem(first));
        service.Items.Add(new ConversionItem(second, status: ConversionStatus.Failed, errorMessage: "retry me"));

        await service.ConvertAllAsync(_root, CancellationToken.None);

        Assert.Equal(new[] { first, second }, worker.Inputs);
        Assert.All(service.Items, item => Assert.Equal(ConversionStatus.Succeeded, item.Status));
    }

    [Fact]
    public async Task ConvertAll_LoadsSuccessfulMarkdownIntoItem()
    {
        var input = Touch("sample.txt");
        var worker = new QueueWorker(markdownFactory: _ => "# Sample");
        var service = new ConversionService(worker);
        service.Items.Add(new ConversionItem(input));

        await service.ConvertAllAsync(_root, CancellationToken.None);

        var item = Assert.Single(service.Items);
        Assert.Equal(ConversionStatus.Succeeded, item.Status);
        Assert.Equal("# Sample", item.MarkdownText);
        Assert.Equal("# Sample", File.ReadAllText(item.OutputPath!));
    }

    [Fact]
    public async Task ConvertAll_StoresWorkerFailureMessage()
    {
        var input = Touch("broken.pdf");
        var worker = new QueueWorker(ok: false, message: "cannot parse");
        var service = new ConversionService(worker);
        service.Items.Add(new ConversionItem(input));

        await service.ConvertAllAsync(_root, CancellationToken.None);

        var item = Assert.Single(service.Items);
        Assert.Equal(ConversionStatus.Failed, item.Status);
        Assert.Equal("cannot parse", item.ErrorMessage);
    }

    [Fact]
    public async Task ConvertAll_CancelsRemainingPendingItems()
    {
        var first = Touch("first.txt");
        var second = Touch("second.txt");
        using var cancellation = new CancellationTokenSource();
        var worker = new QueueWorker(onConverted: () => cancellation.Cancel());
        var service = new ConversionService(worker);
        service.Items.Add(new ConversionItem(first));
        service.Items.Add(new ConversionItem(second));

        await service.ConvertAllAsync(_root, cancellation.Token);

        Assert.Equal(ConversionStatus.Succeeded, service.Items[0].Status);
        Assert.Equal(ConversionStatus.Cancelled, service.Items[1].Status);
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
        File.WriteAllText(path, "input");
        return path;
    }

    private sealed class QueueWorker : IWorkerConverting
    {
        private readonly bool _ok;
        private readonly string? _message;
        private readonly Func<string, string> _markdownFactory;
        private readonly Action? _onConverted;

        public QueueWorker(
            bool ok = true,
            string? message = null,
            Func<string, string>? markdownFactory = null,
            Action? onConverted = null)
        {
            _ok = ok;
            _message = message;
            _markdownFactory = markdownFactory ?? (input => $"# {Path.GetFileNameWithoutExtension(input)}");
            _onConverted = onConverted;
        }

        public WorkerKind WorkerKind => WorkerKind.Ocr;

        public List<string> Inputs { get; } = new();

        public Task<WorkerResponse> ConvertAsync(
            string inputPath,
            string outputPath,
            CancellationToken cancellationToken)
        {
            Inputs.Add(inputPath);
            if (_ok)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
                File.WriteAllText(outputPath, _markdownFactory(inputPath));
            }

            _onConverted?.Invoke();
            return Task.FromResult(new WorkerResponse(
                _ok,
                _ok ? outputPath : null,
                inputPath,
                "ocr",
                _ok ? "markitdown" : null,
                false,
                Array.Empty<string>(),
                _ok ? null : "CONVERSION_FAILED",
                _message));
        }
    }
}
