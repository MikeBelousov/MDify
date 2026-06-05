using System.Text.Json;
using MDify.Windows.Models;
using Xunit;

namespace MDify.Windows.Tests;

public sealed class WorkerResponseTests
{
    [Fact]
    public void WorkerResponse_DeserializesSnakeCaseWorkerJson()
    {
        const string json = """
        {
          "ok": true,
          "output_path": "C:\\out\\notes.md",
          "input_path": "C:\\in\\notes.txt",
          "worker": "mdify-worker-lite",
          "engine": "markitdown",
          "ocr_used": false,
          "warnings": ["one"],
          "error_code": null,
          "message": "done"
        }
        """;

        var response = JsonSerializer.Deserialize<WorkerResponse>(json);

        Assert.NotNull(response);
        Assert.True(response.Ok);
        Assert.Equal(@"C:\out\notes.md", response.OutputPath);
        Assert.Equal(@"C:\in\notes.txt", response.InputPath);
        Assert.False(response.OcrUsed);
        Assert.Null(response.ErrorCode);
    }
}
