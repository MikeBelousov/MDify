namespace MDify.Windows.Models;

public enum WorkerKind
{
    Lite,
    Ocr
}

public static class WorkerKindExtensions
{
    public static string GetExecutableName(this WorkerKind workerKind)
    {
        return workerKind switch
        {
            WorkerKind.Lite => "mdify-worker-lite",
            WorkerKind.Ocr => "mdify-worker-ocr",
            _ => throw new ArgumentOutOfRangeException(nameof(workerKind), workerKind, null)
        };
    }

    public static string GetDisplayName(this WorkerKind workerKind)
    {
        return workerKind switch
        {
            WorkerKind.Lite => "MDify Lite",
            WorkerKind.Ocr => "MDify OCR",
            _ => throw new ArgumentOutOfRangeException(nameof(workerKind), workerKind, null)
        };
    }
}
