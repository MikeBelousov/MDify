using MDify.Windows.Models;

namespace MDify.Windows.Support;

public sealed class OutputRevealPolicy
{
    public bool CanReveal(ConversionItem item)
    {
        return item.Status == ConversionStatus.Succeeded
            && !string.IsNullOrWhiteSpace(item.OutputPath)
            && File.Exists(item.OutputPath);
    }
}
