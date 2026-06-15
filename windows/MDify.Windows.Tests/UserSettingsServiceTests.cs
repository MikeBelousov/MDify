using System.IO;
using MDify.Windows.Models;
using MDify.Windows.Services;
using Xunit;

namespace MDify.Windows.Tests;

public sealed class UserSettingsServiceTests : IDisposable
{
    private readonly string _root = Path.Combine(
        Path.GetTempPath(),
        $"mdify-settings-{Guid.NewGuid():N}");

    [Fact]
    public void OcrVariant_DefaultsToAutoAndPersistsSelection()
    {
        var path = SettingsPath();
        var settings = new UserSettingsService(AppVariant.Ocr, path);

        Assert.Equal(OcrLanguageMode.Auto, settings.LoadOcrLanguage());

        settings.SaveOcrLanguage(OcrLanguageMode.Cyrillic);

        Assert.Equal(
            OcrLanguageMode.Cyrillic,
            new UserSettingsService(AppVariant.Ocr, path).LoadOcrLanguage());
    }

    [Fact]
    public void UnknownOrCorruptValue_ReturnsAuto()
    {
        var path = SettingsPath();
        Directory.CreateDirectory(_root);
        File.WriteAllText(path, """{"OcrLanguage":"Unknown"}""");
        Assert.Equal(
            OcrLanguageMode.Auto,
            new UserSettingsService(AppVariant.Ocr, path).LoadOcrLanguage());

        File.WriteAllText(path, "{broken");
        Assert.Equal(
            OcrLanguageMode.Auto,
            new UserSettingsService(AppVariant.Ocr, path).LoadOcrLanguage());
    }

    [Fact]
    public void LiteVariant_DoesNotReadOrWriteSetting()
    {
        var path = SettingsPath();
        var ocrSettings = new UserSettingsService(AppVariant.Ocr, path);
        ocrSettings.SaveOcrLanguage(OcrLanguageMode.Latin);
        var original = File.ReadAllText(path);

        var liteSettings = new UserSettingsService(AppVariant.Lite, path);
        Assert.Equal(OcrLanguageMode.Auto, liteSettings.LoadOcrLanguage());
        liteSettings.SaveOcrLanguage(OcrLanguageMode.Cyrillic);

        Assert.Equal(original, File.ReadAllText(path));
    }

    public void Dispose()
    {
        if (Directory.Exists(_root))
        {
            Directory.Delete(_root, recursive: true);
        }
    }

    private string SettingsPath() => Path.Combine(_root, "settings.json");
}
