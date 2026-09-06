using System.Diagnostics;
using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _openingGameFolder;
    private Func<string, Task> _openGameFolder = path => Task.Run(() =>
    {
        if (!Path.IsPathFullyQualified(path) || !Directory.Exists(path)) throw new DirectoryNotFoundException(path);
        // Directory is a validated game installation; never build shell arguments from it.
        Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
    });

    private void RefreshGameFolderButton()
    {
        OpenGameFolderButton.Content = T("Открыть папку игры", "Open game folder");
        OpenGameFolderButton.IsEnabled = _game is not null && !_openingGameFolder;
        OpenGameFolderButton.ToolTip = _game?.Directory ?? T("Сначала выберите папку Kohan II.", "Select the Kohan II folder first.");
        GamePathText.ToolTip = _game?.Directory;
    }

    private async void OpenGameFolderButton_Click(object sender, RoutedEventArgs e) => await OpenGameFolderAsync();

    private async Task OpenGameFolderAsync()
    {
        if (_openingGameFolder || _game is null || ConfirmationActive) return;
        _openingGameFolder = true; RefreshGameFolderButton();
        try { await _openGameFolder(_game.Directory); }
        catch (Exception error)
        {
            ActivityStore.Log(error);
            ShowToast(() => T("Не удалось открыть папку игры. Проверьте, что она существует, или выберите её заново.",
                "Could not open the game folder. Check that it exists or select it again."), true);
        }
        finally { _openingGameFolder = false; RefreshGameFolderButton(); }
    }
}
