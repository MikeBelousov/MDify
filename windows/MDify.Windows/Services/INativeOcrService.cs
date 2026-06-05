using MDify.Windows.Models;

namespace MDify.Windows.Services;

public interface INativeOcrService
{
    Task<NativeOcrResult> RecognizeAsync(
        string inputPath,
        CancellationToken cancellationToken);
}
