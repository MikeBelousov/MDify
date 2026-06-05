using System.Windows;
using Microsoft.Win32;

namespace MDify.Windows.Services;

public interface IDialogService
{
    IReadOnlyList<string> PickFiles();

    string? PickFolder(string title);

    FolderScanMode? AskFolderScanMode(string folderPath);

    void ShowError(string message);
}

public sealed class DialogService : IDialogService
{
    public IReadOnlyList<string> PickFiles()
    {
        var dialog = new OpenFileDialog
        {
            Title = "Add files",
            Multiselect = true,
            Filter = "Convertible files|*.pdf;*.docx;*.pptx;*.xlsx;*.xls;*.html;*.htm;*.csv;*.json;*.xml;*.txt;*.md;*.zip;*.epub;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.webp;*.bmp|All files|*.*"
        };

        return dialog.ShowDialog() == true ? dialog.FileNames : Array.Empty<string>();
    }

    public string? PickFolder(string title)
    {
        var dialog = new OpenFolderDialog
        {
            Title = title,
            Multiselect = false
        };

        return dialog.ShowDialog() == true ? dialog.FolderName : null;
    }

    public FolderScanMode? AskFolderScanMode(string folderPath)
    {
        var result = MessageBox.Show(
            $"Include subfolders from {folderPath}?\n\nYes: include subfolders\nNo: top level only\nCancel: do not add this folder",
            "Add Folder",
            MessageBoxButton.YesNoCancel,
            MessageBoxImage.Question);

        return result switch
        {
            MessageBoxResult.Yes => FolderScanMode.Recursive,
            MessageBoxResult.No => FolderScanMode.TopLevelOnly,
            _ => null
        };
    }

    public void ShowError(string message)
    {
        MessageBox.Show(message, "MDify", MessageBoxButton.OK, MessageBoxImage.Error);
    }
}
