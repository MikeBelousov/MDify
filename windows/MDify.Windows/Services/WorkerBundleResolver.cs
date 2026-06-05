using MDify.Windows.Models;

namespace MDify.Windows.Services;

public sealed record WorkerBundleStatus(
    WorkerKind Kind,
    string ExecutablePath,
    bool Exists,
    string Message);

public sealed class WorkerBundleResolver
{
    private readonly string _baseDirectory;

    public WorkerBundleResolver(string? baseDirectory = null)
    {
        _baseDirectory = baseDirectory ?? AppContext.BaseDirectory;
    }

    public string GetWorkerExecutablePath(WorkerKind kind)
    {
        var workerName = kind.GetExecutableName();
        return Path.Combine(_baseDirectory, "Workers", workerName, $"{workerName}.exe");
    }

    public WorkerBundleStatus GetStatus(WorkerKind kind)
    {
        var executablePath = GetWorkerExecutablePath(kind);
        if (!File.Exists(executablePath))
        {
            return new WorkerBundleStatus(
                kind,
                executablePath,
                Exists: false,
                Message: $"Missing worker: {executablePath}");
        }

        return new WorkerBundleStatus(
            kind,
            executablePath,
            Exists: true,
            Message: $"{kind.GetDisplayName()} worker is ready.");
    }

    public WorkerClient CreateClient(
        WorkerKind kind,
        IProcessRunner? runner = null,
        WorkerOcrMode ocrMode = WorkerOcrMode.Auto)
    {
        return new WorkerClient(GetWorkerExecutablePath(kind), kind, runner, ocrMode);
    }
}
