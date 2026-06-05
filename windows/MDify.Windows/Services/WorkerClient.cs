using System.Text.Json;
using MDify.Windows.Models;

namespace MDify.Windows.Services;

public enum WorkerOcrMode
{
    Auto,
    Always,
    Off
}

public interface IWorkerConverting
{
    WorkerKind WorkerKind { get; }

    Task<WorkerResponse> ConvertAsync(
        string inputPath,
        string outputPath,
        CancellationToken cancellationToken);
}

public sealed class WorkerClientException : Exception
{
    public WorkerClientException(string message, Exception? innerException = null)
        : base(message, innerException)
    {
    }
}

public sealed class WorkerClient : IWorkerConverting
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    private readonly string _executablePath;
    private readonly WorkerOcrMode _ocrMode;
    private readonly IProcessRunner _runner;

    public WorkerClient(
        string executablePath,
        WorkerKind workerKind,
        IProcessRunner? runner = null,
        WorkerOcrMode ocrMode = WorkerOcrMode.Auto)
    {
        _executablePath = executablePath;
        WorkerKind = workerKind;
        _runner = runner ?? new ProcessRunner();
        _ocrMode = ocrMode;
    }

    public WorkerKind WorkerKind { get; }

    public async Task<WorkerResponse> ConvertAsync(
        string inputPath,
        string outputPath,
        CancellationToken cancellationToken)
    {
        var arguments = new List<string>
        {
            "--input", inputPath,
            "--output", outputPath,
            "--format", "json"
        };

        if (WorkerKind == WorkerKind.Ocr)
        {
            arguments.AddRange(new[]
            {
                "--ocr", SerializeOcrMode(_ocrMode),
                "--ocr-lang", "cyrillic",
                "--dpi", "300"
            });
        }

        var result = await _runner.RunAsync(_executablePath, arguments, cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(result.Stdout))
        {
            var message = string.IsNullOrWhiteSpace(result.Stderr)
                ? "Worker did not return JSON."
                : result.Stderr.Trim();
            throw new WorkerClientException(message);
        }

        try
        {
            return JsonSerializer.Deserialize<WorkerResponse>(result.Stdout, JsonOptions)
                ?? throw new WorkerClientException("Worker returned empty JSON.");
        }
        catch (JsonException error)
        {
            throw new WorkerClientException("Worker returned invalid JSON.", error);
        }
    }

    private static string SerializeOcrMode(WorkerOcrMode mode)
    {
        return mode switch
        {
            WorkerOcrMode.Auto => "auto",
            WorkerOcrMode.Always => "always",
            WorkerOcrMode.Off => "off",
            _ => throw new ArgumentOutOfRangeException(nameof(mode), mode, null)
        };
    }
}
