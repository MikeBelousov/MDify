using System.Text.Json.Serialization;

namespace MDify.Windows.Models;

public sealed record WorkerResponse(
    [property: JsonPropertyName("ok")] bool Ok,
    [property: JsonPropertyName("output_path")] string? OutputPath,
    [property: JsonPropertyName("input_path")] string InputPath,
    [property: JsonPropertyName("worker")] string Worker,
    [property: JsonPropertyName("engine")] string? Engine,
    [property: JsonPropertyName("ocr_used")] bool OcrUsed,
    [property: JsonPropertyName("warnings")] IReadOnlyList<string> Warnings,
    [property: JsonPropertyName("error_code")] string? ErrorCode,
    [property: JsonPropertyName("message")] string? Message);
