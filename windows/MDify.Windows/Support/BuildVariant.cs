using MDify.Windows.Models;

namespace MDify.Windows.Support;

public static class BuildVariant
{
    public static AppVariant Current
    {
        get
        {
#if MDIFY_WINDOWS_LITE
            return AppVariant.Lite;
#elif MDIFY_WINDOWS_OCR
            return AppVariant.Ocr;
#else
#error A Windows MDify build variant must be selected.
#endif
        }
    }

    public static WorkerKind WorkerKind => Current == AppVariant.Lite
        ? WorkerKind.Lite
        : WorkerKind.Ocr;
}
