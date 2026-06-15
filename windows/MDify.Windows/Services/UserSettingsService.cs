using System.IO;
using System.Text.Json;
using MDify.Windows.Models;
using MDify.Windows.Support;

namespace MDify.Windows.Services;

public sealed class UserSettingsService
{
    private readonly AppVariant _appVariant;
    private readonly string _settingsPath;

    public UserSettingsService(
        AppVariant? appVariant = null,
        string? settingsPath = null)
    {
        _appVariant = appVariant ?? BuildVariant.Current;
        _settingsPath = settingsPath ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MDify",
            "settings.json");
    }

    public OcrLanguageMode LoadOcrLanguage()
    {
        if (_appVariant != AppVariant.Ocr || !File.Exists(_settingsPath))
        {
            return OcrLanguageMode.Auto;
        }

        try
        {
            var settings = JsonSerializer.Deserialize<SettingsDocument>(
                File.ReadAllText(_settingsPath));
            return Enum.TryParse<OcrLanguageMode>(
                settings?.OcrLanguage,
                ignoreCase: true,
                out var language)
                && Enum.IsDefined(language)
                    ? language
                    : OcrLanguageMode.Auto;
        }
        catch (JsonException)
        {
            return OcrLanguageMode.Auto;
        }
        catch (IOException)
        {
            return OcrLanguageMode.Auto;
        }
    }

    public void SaveOcrLanguage(OcrLanguageMode language)
    {
        if (_appVariant != AppVariant.Ocr)
        {
            return;
        }

        var directory = Path.GetDirectoryName(_settingsPath);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        File.WriteAllText(
            _settingsPath,
            JsonSerializer.Serialize(new SettingsDocument(language.ToString())));
    }

    private sealed record SettingsDocument(string OcrLanguage);
}
