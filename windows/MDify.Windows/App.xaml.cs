using System.Windows;
using MDify.Windows.Services;

namespace MDify.Windows;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += (_, args) =>
        {
            MessageBox.Show(
                args.Exception.Message,
                "MDify",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            args.Handled = true;
        };

        if (TryRunNativeOcrDiagnostic(e.Args))
        {
            Shutdown();
            return;
        }

        base.OnStartup(e);
    }

    private static bool TryRunNativeOcrDiagnostic(IReadOnlyList<string> args)
    {
        if (args.Count != 2 || !string.Equals(args[0], "--diagnose-native-ocr", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        try
        {
            var result = new WindowsNativeOcrService()
                .RecognizeAsync(args[1], CancellationToken.None)
                .GetAwaiter()
                .GetResult();
            var preview = result.Markdown.Length > 800 ? $"{result.Markdown[..800]}..." : result.Markdown;
            MessageBox.Show(
                $"Average confidence: {result.AverageConfidence:0.000}\n\n{preview}",
                "MDify Native OCR Diagnostic",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }
        catch (Exception error)
        {
            MessageBox.Show(
                error.Message,
                "MDify Native OCR Diagnostic",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }

        return true;
    }
}
