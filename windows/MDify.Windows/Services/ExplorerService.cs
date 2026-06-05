using System.Diagnostics;
using System.IO;

namespace MDify.Windows.Services;

public interface IExplorerService
{
    void RevealFile(string path);
}

public sealed class ExplorerService : IExplorerService
{
    public void RevealFile(string path)
    {
        if (!File.Exists(path))
        {
            return;
        }

        Process.Start(new ProcessStartInfo
        {
            FileName = "explorer.exe",
            Arguments = $"/select,\"{path}\"",
            UseShellExecute = true
        });
    }
}
