using System.Runtime.InteropServices;
using System.Windows;
using MDify.Windows.Services;
using MDify.Windows.Support;

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

#if MDIFY_WINDOWS_LITE
        if (TryRunNativeOcrDiagnostic(e.Args, out var diagnosticExitCode))
        {
            Shutdown(diagnosticExitCode);
            return;
        }

        CheckNativeOcrReadiness();
#endif
        base.OnStartup(e);
    }

#if MDIFY_WINDOWS_LITE
    private static bool TryRunNativeOcrDiagnostic(
        IReadOnlyList<string> args,
        out int exitCode)
    {
        exitCode = 0;
        if (args.Count != 2 || !string.Equals(args[0], "--diagnose-native-ocr", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        AttachConsole(AttachParentProcess);
        var identity = "unknown";
        var readyState = "unavailable";
        var recognition = "failure";
        var errorType = "none";
        try
        {
            identity = PackageIdentityProbe.Probe().State.ToString().ToLowerInvariant();
            readyState = WindowsNativeOcrService.GetReadyState().ToString();
            _ = new WindowsNativeOcrService()
                .RecognizeAsync(args[1], CancellationToken.None)
                .GetAwaiter()
                .GetResult();
            recognition = "success";
        }
        catch (Exception error)
        {
            errorType = error.GetType().Name;
            exitCode = 1;
        }

        Console.WriteLine($"package_identity={identity}");
        Console.WriteLine($"ready_state={readyState}");
        Console.WriteLine($"recognition={recognition}");
        Console.WriteLine($"error_type={errorType}");
        return true;
    }

    private static void CheckNativeOcrReadiness()
    {
        Microsoft.Windows.AI.AIFeatureReadyState readyState;
        try
        {
            readyState = WindowsNativeOcrService.GetReadyState();
        }
        catch (Exception error)
        {
            ShowNativeOcrUnavailable($"Windows could not inspect the built-in OCR model: {error.Message}");
            return;
        }

        switch (readyState)
        {
            case Microsoft.Windows.AI.AIFeatureReadyState.Ready:
                return;
            case Microsoft.Windows.AI.AIFeatureReadyState.NotReady:
                PrepareNativeOcrWithConsent();
                return;
            case Microsoft.Windows.AI.AIFeatureReadyState.CapabilityMissing:
                ShowNativeOcrUnavailable(
                    "Windows AI denied access to the built-in OCR model. Run the native OCR diagnostic to check package identity and capability access.");
                return;
            case Microsoft.Windows.AI.AIFeatureReadyState.NotSupportedOnCurrentSystem:
                ShowNativeOcrUnavailable(
                    "The built-in OCR model is not supported by this Windows version or hardware. Use MDify OCR on this computer.");
                return;
            case Microsoft.Windows.AI.AIFeatureReadyState.DisabledByUser:
                ShowNativeOcrUnavailable(
                    "The built-in OCR model is disabled in Windows settings.");
                return;
            case Microsoft.Windows.AI.AIFeatureReadyState.NotCompatibleWithSystemHardware:
                ShowNativeOcrUnavailable(
                    "MDify Lite requires a compatible Copilot+ PC with an NPU. Use MDify OCR on this computer.");
                return;
            case Microsoft.Windows.AI.AIFeatureReadyState.OSUpdateNeeded:
                ShowNativeOcrUnavailable(
                    "MDify Lite requires a supported Windows 11 25H2 build or newer. Update Windows or use MDify OCR.");
                return;
            default:
                ShowNativeOcrUnavailable($"Windows Text Recognizer is not ready: {readyState}.");
                return;
        }
    }

    private static void PrepareNativeOcrWithConsent()
    {
        var consent = MessageBox.Show(
            "Windows needs to prepare the built-in text recognition model. Continue?",
            "Prepare Windows OCR",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);
        if (consent == MessageBoxResult.Yes)
        {
            try
            {
                WindowsNativeOcrService.PrepareModelAsync().GetAwaiter().GetResult();
            }
            catch (Exception error)
            {
                ShowNativeOcrUnavailable($"Windows could not prepare the built-in OCR model: {error.Message}");
            }
        }
    }

    private static void ShowNativeOcrUnavailable(string message)
    {
        MessageBox.Show(
            message,
            "MDify Lite OCR unavailable",
            MessageBoxButton.OK,
            MessageBoxImage.Warning);
    }

    private const uint AttachParentProcess = 0xFFFFFFFF;

    [DllImport("kernel32.dll")]
    private static extern bool AttachConsole(uint processId);
#endif
}
