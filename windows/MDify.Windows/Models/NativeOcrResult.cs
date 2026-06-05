namespace MDify.Windows.Models;

public sealed record NativeOcrResult(
    string Markdown,
    double AverageConfidence);
