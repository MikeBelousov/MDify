using System.Collections.ObjectModel;
using MDify.Windows.Models;
using MDify.Windows.Support;

namespace MDify.Windows.Services;

public sealed class ConversionService
{
    private readonly IWorkerConverting _workerClient;
    private readonly OutputFileNamer _namer;

    public ConversionService(
        IWorkerConverting? workerClient = null,
        OutputFileNamer? namer = null)
    {
        _workerClient = workerClient ?? CreateDefaultWorkerClient();
        _namer = namer ?? new OutputFileNamer();
    }

    public ObservableCollection<ConversionItem> Items { get; } = new();

    public void EnqueueFiles(IEnumerable<string> filePaths)
    {
        var existing = Items.Select(item => item.InputPath).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var filePath in filePaths.Where(File.Exists))
        {
            if (existing.Add(filePath))
            {
                Items.Add(new ConversionItem(filePath));
            }
        }
    }

    public int EnqueueFolderScan(FolderScanResult folderScan)
    {
        var existing = Items.Select(item => item.InputPath).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var addedCount = 0;
        foreach (var file in folderScan.Files)
        {
            if (existing.Add(file.Path))
            {
                Items.Add(new ConversionItem(
                    file.Path,
                    sourceRootPath: folderScan.RootPath,
                    relativeOutputPath: file.RelativePath));
                addedCount++;
            }
        }

        return addedCount;
    }

    public void ClearCompleted()
    {
        for (var index = Items.Count - 1; index >= 0; index--)
        {
            if (Items[index].Status is ConversionStatus.Succeeded or ConversionStatus.Failed or ConversionStatus.Cancelled)
            {
                Items.RemoveAt(index);
            }
        }
    }

    public void RemoveItem(Guid id)
    {
        var index = IndexOf(id);
        if (index >= 0)
        {
            Items.RemoveAt(index);
        }
    }

    public async Task ConvertAllAsync(
        string outputDirectory,
        CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(outputDirectory);
        var reservedPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        for (var index = 0; index < Items.Count; index++)
        {
            var item = Items[index];
            if (item.Status is not (ConversionStatus.Pending or ConversionStatus.Failed))
            {
                continue;
            }

            if (cancellationToken.IsCancellationRequested)
            {
                MarkRemainingCancelled(index);
                break;
            }

            var outputPath = _namer.ReserveMarkdownPath(item, outputDirectory, reservedPaths);
            await ConvertItemAsync(index, item, outputPath, cancellationToken);
        }
    }

    private async Task ConvertItemAsync(
        int index,
        ConversionItem item,
        string outputPath,
        CancellationToken cancellationToken)
    {
        Items[index] = item with
        {
            Status = ConversionStatus.Converting,
            OutputPath = outputPath,
            ErrorMessage = null,
            Log = $"Running MDify worker for {item.InputPath}"
        };

        try
        {
            var response = await _workerClient.ConvertAsync(item.InputPath, outputPath, cancellationToken);
            if (!response.Ok)
            {
                Items[index] = Items[index] with
                {
                    Status = ConversionStatus.Failed,
                    ErrorMessage = response.Message ?? response.ErrorCode ?? "Conversion failed.",
                    Log = response.ErrorCode ?? "Worker reported failure."
                };
                return;
            }

            var markdown = await File.ReadAllTextAsync(outputPath, CancellationToken.None);
            Items[index] = Items[index] with
            {
                Status = ConversionStatus.Succeeded,
                MarkdownText = markdown,
                OutputPath = outputPath,
                Log = WorkerLog(response)
            };
        }
        catch (OperationCanceledException)
        {
            Items[index] = Items[index] with { Status = ConversionStatus.Cancelled };
            MarkRemainingCancelled(index + 1);
        }
        catch (Exception error)
        {
            Items[index] = Items[index] with
            {
                Status = ConversionStatus.Failed,
                ErrorMessage = error.Message,
                Log = error.Message
            };
        }
    }

    private void MarkRemainingCancelled(int startIndex)
    {
        for (var index = startIndex; index < Items.Count; index++)
        {
            if (Items[index].Status is ConversionStatus.Pending or ConversionStatus.Failed)
            {
                Items[index] = Items[index] with { Status = ConversionStatus.Cancelled };
            }
        }
    }

    private int IndexOf(Guid id)
    {
        for (var index = 0; index < Items.Count; index++)
        {
            if (Items[index].Id == id)
            {
                return index;
            }
        }

        return -1;
    }

    private static string WorkerLog(WorkerResponse response)
    {
        var lines = new List<string>
        {
            $"Worker: {response.Worker}",
            $"Engine: {response.Engine ?? "unknown"}",
            $"OCR used: {(response.OcrUsed ? "yes" : "no")}"
        };
        if (response.Warnings.Count > 0)
        {
            lines.Add($"Warnings: {string.Join("; ", response.Warnings)}");
        }

        return string.Join(Environment.NewLine, lines);
    }

    private static IWorkerConverting CreateDefaultWorkerClient()
    {
        var resolver = new WorkerBundleResolver();
        var preflightClient = resolver.CreateClient(WorkerKind.Ocr, ocrMode: WorkerOcrMode.Off);
        var rapidOcrClient = resolver.CreateClient(WorkerKind.Ocr, ocrMode: WorkerOcrMode.Always);
        return new NativeOcrRoutingClient(
            WorkerKind.Ocr,
            preflightClient,
            rapidOcrClient,
            new WindowsNativeOcrService());
    }
}
