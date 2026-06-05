using MDify.Windows.Services;
using MDify.Windows.Models;
using MDify.Windows.Support;

namespace MDify.Windows.Tests;

public sealed class FolderImportServiceTests : IDisposable
{
    private readonly string _root = Path.Combine(Path.GetTempPath(), $"mdify-folder-{Guid.NewGuid():N}");

    public FolderImportServiceTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void Scan_TopLevel_SkipsHiddenSymlinksPackagesAndNestedFiles()
    {
        var fixture = MakeFixture();

        var result = new FolderImportService().Scan(_root, FolderScanMode.TopLevelOnly);

        Assert.Equal(new[] { "report.pdf" }, result.Files.Select(file => Path.GetFileName(file.Path)).ToArray());
        Assert.True(result.HasSubfolders);
        Assert.DoesNotContain(result.Files, file => file.RelativePath.Contains("nested", StringComparison.OrdinalIgnoreCase));
        Assert.DoesNotContain(result.Files, file => file.Path.Contains("hidden.pdf", StringComparison.OrdinalIgnoreCase));
        Assert.DoesNotContain(result.Files, file => file.Path.Contains(".app", StringComparison.OrdinalIgnoreCase));
        Assert.DoesNotContain(result.Files, file => file.Path.Contains(".bundle", StringComparison.OrdinalIgnoreCase));
        Assert.DoesNotContain(result.Files, file => file.Path.Contains("hiddenDir", StringComparison.OrdinalIgnoreCase));
        if (fixture.CreatedSymlink)
        {
            Assert.DoesNotContain(result.Files, file => file.Path.Contains("linked.txt", StringComparison.OrdinalIgnoreCase));
        }
    }

    [Fact]
    public void Scan_Recursive_IncludesNestedSupportedFiles()
    {
        MakeFixture();

        var result = new FolderImportService().Scan(_root, FolderScanMode.Recursive);

        Assert.Equal(
            new[] { Path.Combine("nested", "deep", "deck.pptx"), Path.Combine("nested", "notes.txt"), "report.pdf" },
            result.Files.Select(file => file.RelativePath).Order(StringComparer.Ordinal).ToArray());
        Assert.True(result.HasSubfolders);
    }

    [Fact]
    public void Scan_UsesDefaultOcrPolicy()
    {
        File.WriteAllText(Path.Combine(_root, "scan.png"), "");

        var result = new FolderImportService().Scan(_root, FolderScanMode.TopLevelOnly);

        Assert.Equal("scan.png", Assert.Single(result.Files).RelativePath);
    }

    [Fact]
    public void ConvertibleFilePolicy_LiteAndOcrMirrorWorkerExtensions()
    {
        var lite = new ConvertibleFilePolicy(WorkerKind.Lite);
        var ocr = new ConvertibleFilePolicy(WorkerKind.Ocr);

        Assert.True(lite.IsConvertibleFile("report.pdf"));
        Assert.True(lite.IsConvertibleFile("notes.md"));
        Assert.True(lite.IsConvertibleFile("archive.zip"));
        Assert.False(lite.IsConvertibleFile("scan.png"));
        Assert.True(ocr.IsConvertibleFile("scan.png"));
        Assert.True(ocr.IsConvertibleFile("photo.jpeg"));
        Assert.False(ocr.IsConvertibleFile("program.exe"));
    }

    private FixtureState MakeFixture()
    {
        Directory.CreateDirectory(Path.Combine(_root, "nested", "deep"));
        Directory.CreateDirectory(Path.Combine(_root, "Preview.app"));
        Directory.CreateDirectory(Path.Combine(_root, "Plugin.bundle"));
        var hiddenDirectory = Path.Combine(_root, "hiddenDir");
        Directory.CreateDirectory(hiddenDirectory);

        File.WriteAllText(Path.Combine(_root, "report.pdf"), "");
        File.WriteAllText(Path.Combine(_root, "todo.exe"), "");
        var hiddenFile = Path.Combine(_root, "hidden.pdf");
        File.WriteAllText(hiddenFile, "");
        File.WriteAllText(Path.Combine(_root, "nested", "notes.txt"), "");
        File.WriteAllText(Path.Combine(_root, "nested", "deep", "deck.pptx"), "");
        File.WriteAllText(Path.Combine(_root, "Preview.app", "inside.pdf"), "");
        File.WriteAllText(Path.Combine(_root, "Plugin.bundle", "inside.pdf"), "");
        File.WriteAllText(Path.Combine(hiddenDirectory, "inside.pdf"), "");

        File.SetAttributes(hiddenFile, File.GetAttributes(hiddenFile) | FileAttributes.Hidden);
        File.SetAttributes(hiddenDirectory, File.GetAttributes(hiddenDirectory) | FileAttributes.Hidden);

        var createdSymlink = TryCreateSymlink(
            Path.Combine(_root, "linked.txt"),
            Path.Combine(_root, "nested", "notes.txt"));

        return new FixtureState(createdSymlink);
    }

    private static bool TryCreateSymlink(string linkPath, string targetPath)
    {
        try
        {
            File.CreateSymbolicLink(linkPath, targetPath);
            return true;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
        catch (PlatformNotSupportedException)
        {
            return false;
        }
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            ResetAttributes(_root);
            Directory.Delete(_root, recursive: true);
        }
    }

    private static void ResetAttributes(string path)
    {
        var options = new EnumerationOptions
        {
            AttributesToSkip = 0,
            IgnoreInaccessible = true,
            RecurseSubdirectories = true
        };

        foreach (var entry in Directory.EnumerateFileSystemEntries(path, "*", options))
        {
            TrySetNormalAttributes(entry);
        }

        TrySetNormalAttributes(path);
    }

    private static void TrySetNormalAttributes(string path)
    {
        try
        {
            File.SetAttributes(path, FileAttributes.Normal);
        }
        catch (IOException)
        {
        }
        catch (UnauthorizedAccessException)
        {
        }
    }

    private sealed record FixtureState(bool CreatedSymlink);
}
