using System.IO;
using MDify.Windows.Models;
using MDify.Windows.Services;

namespace MDify.Windows.Tests;

public sealed class WorkerClientTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"mdify-worker-client-{Guid.NewGuid():N}");

    public WorkerClientTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public async Task ProcessRunner_CapturesStdout()
    {
        var result = await new ProcessRunner().RunAsync(
            "cmd.exe",
            new[] { "/c", "echo hello" },
            CancellationToken.None);

        Assert.Equal(0, result.ExitCode);
        Assert.Equal("hello", result.Stdout.Trim());
    }

    [Fact]
    public async Task ProcessRunner_CapturesStderrAndExitCode()
    {
        var result = await new ProcessRunner().RunAsync(
            "cmd.exe",
            new[] { "/c", "echo error 1>&2 & exit /b 7" },
            CancellationToken.None);

        Assert.Equal(7, result.ExitCode);
        Assert.Equal("error", result.Stderr.Trim());
    }

    [Fact]
    public async Task ProcessRunner_ReportsLaunchFailure()
    {
        var error = await Assert.ThrowsAsync<ProcessRunnerException>(() =>
            new ProcessRunner().RunAsync(
                Path.Combine(_root, "missing.exe"),
                Array.Empty<string>(),
                CancellationToken.None));

        Assert.Contains("Could not launch process", error.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ProcessRunner_CancelsLongRunningProcess()
    {
        using var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            new ProcessRunner().RunAsync(
                "cmd.exe",
                new[] { "/c", "ping -n 30 127.0.0.1 > nul" },
                cancellation.Token));
    }

    [Fact]
    public async Task WorkerClient_DecodesWorkerJson()
    {
        const string json = """
        {"ok":true,"output_path":"C:\\out.md","input_path":"C:\\in.txt","worker":"lite","engine":"markitdown","ocr_used":false,"warnings":[]}
        """;
        var runner = new FakeProcessRunner(new ProcessRunResult(0, json, ""));
        var client = new WorkerClient(@"C:\Workers\mdify-worker-lite.exe", WorkerKind.Lite, runner);

        var response = await client.ConvertAsync(@"C:\in.txt", @"C:\out.md", CancellationToken.None);

        Assert.True(response.Ok);
        Assert.Equal(@"C:\out.md", response.OutputPath);
        Assert.Equal("lite", response.Worker);
        Assert.Equal("markitdown", response.Engine);
        Assert.False(response.OcrUsed);
    }

    [Fact]
    public async Task WorkerClient_PassesOcrArguments()
    {
        const string json = """
        {"ok":true,"output_path":"C:\\out.md","input_path":"C:\\scan.png","worker":"ocr","engine":"rapidocr","ocr_used":true,"warnings":[]}
        """;
        var runner = new FakeProcessRunner(new ProcessRunResult(0, json, ""));
        var client = new WorkerClient(@"C:\Workers\mdify-worker-ocr.exe", WorkerKind.Ocr, runner);

        await client.ConvertAsync(@"C:\scan.png", @"C:\out.md", CancellationToken.None);

        Assert.Equal(
            new[]
            {
                "--input", @"C:\scan.png",
                "--output", @"C:\out.md",
                "--format", "json",
                "--ocr", "auto",
                "--ocr-lang", "cyrillic",
                "--dpi", "300"
            },
            runner.LastArguments);
    }

    [Theory]
    [InlineData(WorkerOcrMode.Always, "always")]
    [InlineData(WorkerOcrMode.Off, "off")]
    public async Task WorkerClient_PassesExplicitOcrMode(WorkerOcrMode mode, string expectedValue)
    {
        const string json = """
        {"ok":true,"output_path":"C:\\out.md","input_path":"C:\\scan.pdf","worker":"ocr","engine":"rapidocr","ocr_used":true,"warnings":[]}
        """;
        var runner = new FakeProcessRunner(new ProcessRunResult(0, json, ""));
        var client = new WorkerClient(@"C:\Workers\mdify-worker-ocr.exe", WorkerKind.Ocr, runner, mode);

        await client.ConvertAsync(@"C:\scan.pdf", @"C:\out.md", CancellationToken.None);

        Assert.Equal(
            new[] { "--ocr", expectedValue, "--ocr-lang", "cyrillic", "--dpi", "300" },
            runner.LastArguments.TakeLast(6));
    }

    [Fact]
    public async Task WorkerClient_ThrowsForEmptyStdout()
    {
        var runner = new FakeProcessRunner(new ProcessRunResult(1, "", "worker failed"));
        var client = new WorkerClient(@"C:\Workers\mdify-worker-lite.exe", WorkerKind.Lite, runner);

        var error = await Assert.ThrowsAsync<WorkerClientException>(() =>
            client.ConvertAsync(@"C:\in.txt", @"C:\out.md", CancellationToken.None));

        Assert.Equal("worker failed", error.Message);
    }

    [Fact]
    public async Task WorkerClient_ThrowsForMalformedJson()
    {
        var runner = new FakeProcessRunner(new ProcessRunResult(0, "not-json", ""));
        var client = new WorkerClient(@"C:\Workers\mdify-worker-lite.exe", WorkerKind.Lite, runner);

        var error = await Assert.ThrowsAsync<WorkerClientException>(() =>
            client.ConvertAsync(@"C:\in.txt", @"C:\out.md", CancellationToken.None));

        Assert.Contains("invalid JSON", error.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void WorkerBundleResolver_ResolvesInstalledWorkers()
    {
        var resolver = new WorkerBundleResolver(_root);

        var lite = resolver.GetWorkerExecutablePath(WorkerKind.Lite);
        var ocr = resolver.GetWorkerExecutablePath(WorkerKind.Ocr);

        Assert.Equal(Path.Combine(_root, "Workers", "mdify-worker-lite", "mdify-worker-lite.exe"), lite);
        Assert.Equal(Path.Combine(_root, "Workers", "mdify-worker-ocr", "mdify-worker-ocr.exe"), ocr);
    }

    [Fact]
    public void WorkerBundleResolver_ReportsMissingWorkerStatus()
    {
        var status = new WorkerBundleResolver(_root).GetStatus(WorkerKind.Ocr);

        Assert.False(status.Exists);
        Assert.Equal(WorkerKind.Ocr, status.Kind);
        Assert.Contains("Missing worker", status.Message, StringComparison.OrdinalIgnoreCase);
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    private sealed class FakeProcessRunner : IProcessRunner
    {
        private readonly ProcessRunResult _result;

        public FakeProcessRunner(ProcessRunResult result)
        {
            _result = result;
        }

        public IReadOnlyList<string> LastArguments { get; private set; } = Array.Empty<string>();

        public Task<ProcessRunResult> RunAsync(
            string executablePath,
            IReadOnlyList<string> arguments,
            CancellationToken cancellationToken)
        {
            LastArguments = arguments.ToArray();
            return Task.FromResult(_result);
        }
    }
}
