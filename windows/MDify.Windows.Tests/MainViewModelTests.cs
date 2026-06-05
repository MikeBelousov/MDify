using System.IO;
using MDify.Windows.Models;
using MDify.Windows.Services;
using MDify.Windows.ViewModels;

namespace MDify.Windows.Tests;

public sealed class MainViewModelTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"mdify-vm-{Guid.NewGuid():N}");

    public MainViewModelTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void AddFilesCommand_EnqueuesPickedFiles()
    {
        var input = Touch("notes.txt");
        var dialog = new FakeDialogService { PickedFiles = new[] { input } };
        var viewModel = MakeViewModel(dialog);

        viewModel.AddFilesCommand.Execute(null);

        Assert.Equal(input, Assert.Single(viewModel.Items).InputPath);
        Assert.Equal(ConversionStatus.Pending, viewModel.SelectedItem?.Status);
    }

    [Fact]
    public void CopyMarkdownCommand_CopiesSelectedMarkdown()
    {
        var clipboard = new FakeClipboardService();
        var viewModel = MakeViewModel(clipboard: clipboard);
        viewModel.Items.Add(new ConversionItem(Touch("notes.txt"), markdownText: "# Notes"));

        viewModel.CopyMarkdownCommand.Execute(null);

        Assert.Equal("# Notes", clipboard.Text);
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    private MainViewModel MakeViewModel(
        FakeDialogService? dialog = null,
        FakeClipboardService? clipboard = null)
    {
        return new MainViewModel(
            new ConversionService(new FakeWorker()),
            new FolderImportService(),
            dialog ?? new FakeDialogService(),
            clipboard ?? new FakeClipboardService(),
            new FakeExplorerService());
    }

    private string Touch(string fileName)
    {
        var path = Path.Combine(_root, fileName);
        File.WriteAllText(path, "input");
        return path;
    }

    private sealed class FakeDialogService : IDialogService
    {
        public IReadOnlyList<string> PickedFiles { get; init; } = Array.Empty<string>();

        public IReadOnlyList<string> PickFiles() => PickedFiles;

        public string? PickFolder(string title) => null;

        public FolderScanMode? AskFolderScanMode(string folderPath) => FolderScanMode.TopLevelOnly;

        public void ShowError(string message)
        {
        }
    }

    private sealed class FakeClipboardService : IClipboardService
    {
        public string? Text { get; private set; }

        public void SetText(string text)
        {
            Text = text;
        }
    }

    private sealed class FakeExplorerService : IExplorerService
    {
        public void RevealFile(string path)
        {
        }
    }

    private sealed class FakeWorker : IWorkerConverting
    {
        public WorkerKind WorkerKind => WorkerKind.Ocr;

        public Task<WorkerResponse> ConvertAsync(
            string inputPath,
            string outputPath,
            CancellationToken cancellationToken)
        {
            throw new NotImplementedException();
        }
    }
}
