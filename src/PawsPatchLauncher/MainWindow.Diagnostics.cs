using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly DiagnosticArchiveHistory _diagnosticHistory = new(ActivityStore.Root);
    private DiagnosticArchiveReference? _lastDiagnosticArchive, _sessionDiagnosticArchive;
    private bool _diagnosticArchiveExists, _showingDiagnosticArchive, _diagnosticsClosed;
    private int _diagnosticsRefreshVersion;
    private Func<string, Task> _revealDiagnosticArchive = ShellFileReveal.ShowAsync;

    private void InitializeDiagnosticsUi()
    {
        Loaded += async (_, _) => await RefreshDiagnosticsArchiveAsync();
        Activated += async (_, _) => await RefreshDiagnosticsArchiveAsync();
        Closed += (_, _) => { _diagnosticsClosed = true; _diagnosticsRefreshVersion++; };
    }

    private async Task RefreshDiagnosticsArchiveAsync()
    {
        if (_diagnosticsClosed) return;
        var version = ++_diagnosticsRefreshVersion;
        var session = _sessionDiagnosticArchive;
        var result = await Task.Run(() =>
        {
            var record = _diagnosticHistory.Read();
            if (session is not null && (record is null || session.CreatedAtUtc > record.CreatedAtUtc)) record = session;
            return (Record: record, Exists: DiagnosticArchiveHistory.Exists(record));
        });
        if (_diagnosticsClosed || version != _diagnosticsRefreshVersion) return;
        _lastDiagnosticArchive = result.Record;
        _diagnosticArchiveExists = result.Exists;
        RenderDiagnosticsArchive();
    }

    private void RenderDiagnosticsArchive()
    {
        ShowDiagnosticsArchiveButton.Content = T("Показать архив", "Show archive");
        ShowDiagnosticsArchiveButton.IsEnabled = _diagnosticArchiveExists && !_showingDiagnosticArchive;
        if (_lastDiagnosticArchive is null)
            DiagnosticsArchiveInfoText.Text = T("Архив ещё не создан.", "No archive has been created yet.");
        else if (!_diagnosticArchiveExists)
            DiagnosticsArchiveInfoText.Text = T("Последний архив удалён или перемещён. Создайте новый.", "The last archive was deleted or moved. Create a new one.");
        else
            DiagnosticsArchiveInfoText.Text = T("Последний: ", "Latest: ") + Path.GetFileName(_lastDiagnosticArchive.Path)
                + "\n" + _lastDiagnosticArchive.CreatedAtUtc.ToLocalTime().ToString(_text.Language == "ru" ? "dd.MM.yyyy HH:mm" : "yyyy-MM-dd HH:mm");
        DiagnosticsArchiveInfoText.ToolTip = _lastDiagnosticArchive?.Path;
        ShowDiagnosticsArchiveButton.ToolTip = _diagnosticArchiveExists
            ? T("Открыть папку и выделить последний созданный архив.", "Open the folder and select the latest archive.")
            : DiagnosticsArchiveInfoText.Text;
    }

    private async Task<bool> RememberCreatedDiagnosticsAsync(string path)
    {
        // Called only after the collector has successfully completed the ZIP.
        var record = await Task.Run(() => DiagnosticArchiveHistory.CreateReference(path));
        _sessionDiagnosticArchive = record;
        var saved = true;
        try { await Task.Run(() => _diagnosticHistory.Save(record)); }
        catch (Exception error)
        {
            saved = false;
            ActivityStore.Log(error);
            ShowToast(() => T("Архив создан, но не удалось запомнить его после перезапуска. Сейчас его можно показать кнопкой ниже.",
                "The archive was created, but its location could not be saved for restart. You can still show it now."), true);
        }
        await RefreshDiagnosticsArchiveAsync();
        return saved;
    }

    private async void ShowDiagnosticsArchiveButton_Click(object sender, RoutedEventArgs e) => await ShowLastDiagnosticsArchiveAsync();

    private async Task ShowLastDiagnosticsArchiveAsync()
    {
        if (_showingDiagnosticArchive || _diagnosticsClosed) return;
        _showingDiagnosticArchive = true; RenderDiagnosticsArchive();
        try
        {
            await RefreshDiagnosticsArchiveAsync();
            if (_diagnosticsClosed) return;
            if (!_diagnosticArchiveExists || _lastDiagnosticArchive is null)
            {
                ShowToast(() => T("Последний архив не найден. Создайте новый архив диагностики.", "The last archive was not found. Create a new diagnostic archive."), true);
                return;
            }
            await _revealDiagnosticArchive(_lastDiagnosticArchive.Path);
        }
        catch (Exception error)
        {
            ActivityStore.Log(error);
            await RefreshDiagnosticsArchiveAsync();
            ShowToast(() => T("Не удалось показать архив в Проводнике. Полный путь указан в подсказке к имени файла.", "Could not show the archive in File Explorer. Hover over its filename to see the full path."), true);
        }
        finally { _showingDiagnosticArchive = false; if (!_diagnosticsClosed) RenderDiagnosticsArchive(); }
    }
}
