using System.Collections.ObjectModel;
using System.Collections.Specialized;
using System.ComponentModel;
using System.IO;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using MDify.Windows.Models;
using MDify.Windows.Services;
using MDify.Windows.Support;

namespace MDify.Windows.ViewModels;

public sealed class MainViewModel : INotifyPropertyChanged
{
    private readonly ConversionService _conversionService;
    private readonly FolderImportService _folderImportService;
    private readonly IDialogService _dialogService;
    private readonly IClipboardService _clipboardService;
    private readonly IExplorerService _explorerService;
    private readonly OutputRevealPolicy _revealPolicy = new();
    private CancellationTokenSource? _conversionCancellation;
    private ConversionItem? _selectedItem;
    private bool _isConverting;
    private string _outputFolder;
    private string _statusText = "Ready";

    public MainViewModel()
        : this(
            new ConversionService(),
            new FolderImportService(),
            new DialogService(),
            new ClipboardService(),
            new ExplorerService())
    {
    }

    public MainViewModel(
        ConversionService conversionService,
        FolderImportService folderImportService,
        IDialogService dialogService,
        IClipboardService clipboardService,
        IExplorerService explorerService)
    {
        _conversionService = conversionService;
        _folderImportService = folderImportService;
        _dialogService = dialogService;
        _clipboardService = clipboardService;
        _explorerService = explorerService;
        _outputFolder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            "MDify");

        AddFilesCommand = new RelayCommand(AddFiles, () => !IsConverting);
        AddFolderCommand = new RelayCommand(AddFolder, () => !IsConverting);
        ChooseOutputFolderCommand = new RelayCommand(ChooseOutputFolder, () => !IsConverting);
        ConvertAllCommand = new AsyncRelayCommand(ConvertAllAsync, () => !IsConverting && Items.Count > 0);
        CancelCommand = new RelayCommand(Cancel, () => IsConverting);
        CopyMarkdownCommand = new RelayCommand(CopyMarkdown, () => !string.IsNullOrEmpty(SelectedItem?.MarkdownText));
        RevealOutputCommand = new RelayCommand(RevealOutput, () => SelectedItem is not null && _revealPolicy.CanReveal(SelectedItem));
        RemoveSelectedCommand = new RelayCommand(RemoveSelected, () => SelectedItem is not null && !IsConverting);
        ClearCompletedCommand = new RelayCommand(ClearCompleted, () => !IsConverting);

        Items.CollectionChanged += OnItemsChanged;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<ConversionItem> Items => _conversionService.Items;

    public ConversionItem? SelectedItem
    {
        get => _selectedItem ?? Items.FirstOrDefault();
        set
        {
            if (_selectedItem == value)
            {
                return;
            }

            _selectedItem = value;
            OnPropertyChanged();
            OnPropertyChanged(nameof(PreviewText));
            OnPropertyChanged(nameof(LogText));
            RaiseCommandStates();
        }
    }

    public string PreviewText => SelectedItem?.MarkdownText ?? "";

    public string LogText => SelectedItem?.Log ?? "";

    public string OutputFolder
    {
        get => _outputFolder;
        set
        {
            if (_outputFolder == value)
            {
                return;
            }

            _outputFolder = value;
            OnPropertyChanged();
        }
    }

    public string StatusText
    {
        get => _statusText;
        private set
        {
            if (_statusText == value)
            {
                return;
            }

            _statusText = value;
            OnPropertyChanged();
        }
    }

    public bool IsConverting
    {
        get => _isConverting;
        private set
        {
            if (_isConverting == value)
            {
                return;
            }

            _isConverting = value;
            OnPropertyChanged();
            RaiseCommandStates();
        }
    }

    public ICommand AddFilesCommand { get; }

    public ICommand AddFolderCommand { get; }

    public ICommand ChooseOutputFolderCommand { get; }

    public ICommand ConvertAllCommand { get; }

    public ICommand CancelCommand { get; }

    public ICommand CopyMarkdownCommand { get; }

    public ICommand RevealOutputCommand { get; }

    public ICommand RemoveSelectedCommand { get; }

    public ICommand ClearCompletedCommand { get; }

    public async Task AddDroppedPathsAsync(IEnumerable<string> paths)
    {
        foreach (var group in paths.GroupBy(Directory.Exists))
        {
            if (group.Key)
            {
                foreach (var directory in group)
                {
                    AddFolderPath(directory);
                }
            }
            else
            {
                _conversionService.EnqueueFiles(group);
            }
        }

        await Task.CompletedTask;
        EnsureSelection();
        UpdateStatus();
    }

    private void AddFiles()
    {
        _conversionService.EnqueueFiles(_dialogService.PickFiles());
        EnsureSelection();
        UpdateStatus();
    }

    private void AddFolder()
    {
        var folder = _dialogService.PickFolder("Add folder");
        if (folder is null)
        {
            return;
        }

        AddFolderPath(folder);
        EnsureSelection();
        UpdateStatus();
    }

    private void AddFolderPath(string folder)
    {
        try
        {
            var topLevelScan = _folderImportService.Scan(folder, FolderScanMode.TopLevelOnly);
            var mode = topLevelScan.HasSubfolders
                ? _dialogService.AskFolderScanMode(folder)
                : FolderScanMode.TopLevelOnly;
            if (mode is null)
            {
                return;
            }

            var scan = mode == FolderScanMode.TopLevelOnly
                ? topLevelScan
                : _folderImportService.Scan(folder, FolderScanMode.Recursive);
            var added = _conversionService.EnqueueFolderScan(scan);
            StatusText = $"Added {added} file(s); skipped {scan.SkippedUnsupportedCount}.";
        }
        catch (Exception error)
        {
            _dialogService.ShowError(error.Message);
        }
    }

    private void ChooseOutputFolder()
    {
        var folder = _dialogService.PickFolder("Choose output folder");
        if (folder is not null)
        {
            OutputFolder = folder;
        }
    }

    private async Task ConvertAllAsync()
    {
        IsConverting = true;
        _conversionCancellation = new CancellationTokenSource();
        try
        {
            await _conversionService.ConvertAllAsync(OutputFolder, _conversionCancellation.Token);
            StatusText = "Conversion complete";
        }
        catch (Exception error)
        {
            StatusText = "Conversion failed";
            _dialogService.ShowError(error.Message);
        }
        finally
        {
            _conversionCancellation.Dispose();
            _conversionCancellation = null;
            IsConverting = false;
            OnPropertyChanged(nameof(PreviewText));
            OnPropertyChanged(nameof(LogText));
            RaiseCommandStates();
        }
    }

    private void Cancel()
    {
        _conversionCancellation?.Cancel();
        StatusText = "Cancelling...";
    }

    private void CopyMarkdown()
    {
        if (!string.IsNullOrEmpty(SelectedItem?.MarkdownText))
        {
            _clipboardService.SetText(SelectedItem.MarkdownText);
            StatusText = "Markdown copied";
        }
    }

    private void RevealOutput()
    {
        if (SelectedItem?.OutputPath is not null)
        {
            _explorerService.RevealFile(SelectedItem.OutputPath);
        }
    }

    private void RemoveSelected()
    {
        if (SelectedItem is null)
        {
            return;
        }

        _conversionService.RemoveItem(SelectedItem.Id);
        EnsureSelection();
        UpdateStatus();
    }

    private void ClearCompleted()
    {
        _conversionService.ClearCompleted();
        EnsureSelection();
        UpdateStatus();
    }

    private void OnItemsChanged(object? sender, NotifyCollectionChangedEventArgs e)
    {
        EnsureSelection();
        OnPropertyChanged(nameof(Items));
        OnPropertyChanged(nameof(PreviewText));
        OnPropertyChanged(nameof(LogText));
        RaiseCommandStates();
        UpdateStatus();
    }

    private void EnsureSelection()
    {
        if (SelectedItem is null || !Items.Contains(SelectedItem))
        {
            SelectedItem = Items.FirstOrDefault();
        }
    }

    private void UpdateStatus()
    {
        StatusText = $"{Items.Count} item(s) queued";
    }

    private void RaiseCommandStates()
    {
        foreach (var command in new[]
        {
            AddFilesCommand,
            AddFolderCommand,
            ChooseOutputFolderCommand,
            ConvertAllCommand,
            CancelCommand,
            CopyMarkdownCommand,
            RevealOutputCommand,
            RemoveSelectedCommand,
            ClearCompletedCommand
        })
        {
            switch (command)
            {
                case RelayCommand relay:
                    relay.RaiseCanExecuteChanged();
                    break;
                case AsyncRelayCommand asyncRelay:
                    asyncRelay.RaiseCanExecuteChanged();
                    break;
            }
        }
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
