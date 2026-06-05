using MDify.Windows.Models;

namespace MDify.Windows.ViewModels;

public sealed class ConversionItemViewModel
{
    public ConversionItemViewModel(ConversionItem item)
    {
        Item = item;
    }

    public ConversionItem Item { get; }

    public string DisplayName => Item.DisplayName;

    public string? RelativePath => Item.FolderRelativeDisplayPath;

    public string Status => Item.Status.ToString();

    public string MarkdownText => Item.MarkdownText;
}
