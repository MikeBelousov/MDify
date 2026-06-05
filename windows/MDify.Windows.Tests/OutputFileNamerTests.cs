using MDify.Windows.Models;
using MDify.Windows.Support;

namespace MDify.Windows.Tests;

public sealed class OutputFileNamerTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"mdify-namer-{Guid.NewGuid():N}");

    public OutputFileNamerTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void GetMarkdownPath_ChangesInputExtensionToMarkdown()
    {
        var result = new OutputFileNamer().GetMarkdownPath(
            Path.Combine(_root, "input", "notes.txt"),
            _root);

        Assert.Equal(Path.Combine(_root, "notes.md"), result);
    }

    [Fact]
    public void GetMarkdownPath_AppendsNumberWhenOutputExists()
    {
        File.WriteAllText(Path.Combine(_root, "notes.md"), "");

        var result = new OutputFileNamer().GetMarkdownPath(
            Path.Combine(_root, "notes.txt"),
            _root);

        Assert.Equal(Path.Combine(_root, "notes 2.md"), result);
    }

    [Fact]
    public void GetMarkdownPath_ReservesNamesDuringBatch()
    {
        var reserved = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            Path.Combine(_root, "notes.md")
        };

        var result = new OutputFileNamer().GetMarkdownPath(
            Path.Combine(_root, "notes.txt"),
            _root,
            reserved);

        Assert.Equal(Path.Combine(_root, "notes 2.md"), result);
    }

    [Fact]
    public void GetMarkdownPath_PreservesFolderImportRelativePathUnderOutputRoot()
    {
        var item = new ConversionItem(
            InputPath: Path.Combine(_root, "source", "nested", "notes.txt"),
            SourceRootPath: Path.Combine(_root, "source"),
            RelativeOutputPath: Path.Combine("nested", "notes.txt"));

        var result = new OutputFileNamer().GetMarkdownPath(item, _root);

        Assert.Equal(Path.Combine(_root, "nested", "notes.md"), result);
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }
}
