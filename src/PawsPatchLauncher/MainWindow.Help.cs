using System.Diagnostics;
using System.Windows;
using System.Windows.Navigation;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private string BrowserOpenError() => T("Не удалось открыть браузер. Попробуйте ещё раз или откройте ссылку вручную.",
        "Could not open the browser. Try again or open the link manually.");
    private const string ArcaneWarsDiscordInvite = "https://discord.gg/krCK7DDwyz";
    private string ArcaneWarsAuthorText => T("Автор Arcane Wars: ", "Arcane Wars author: ") + "Darquan Mortis";
    private bool _openingHelpLink;
    private Func<string, Task> _openHelpLink = url => Task.Run(() =>
    {
        using var browser = Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    });

    private void RenderArcaneWarsCredit(string helpKey)
    {
        HelpLinkErrorText.Visibility = Visibility.Collapsed;
        ArcaneWarsCreditPanel.Visibility = helpKey == "modules.core" && GameMod.IsArcaneWars(_settings) ? Visibility.Visible : Visibility.Collapsed;
        ArcaneWarsAuthorLabel.Text = T("Автор Arcane Wars: ", "Arcane Wars author: ");
        ArcaneWarsDistributionText.Text = T("Базовый мод опубликован на ModDB. Патч 0.82.1.8 fix v2 автор распространяет в Discord.",
            "The base mod is published on ModDB. The author distributes patch 0.82.1.8 fix v2 on Discord.");
    }

    private async void ArcaneWarsModDb_RequestNavigate(object sender, RequestNavigateEventArgs e)
    {
        e.Handled = true;
        if (_openingHelpLink || e.Uri.AbsoluteUri != ModDbDownload.ArcanePage) return;
        _openingHelpLink = true;
        try { await OpenConfirmedLinkAsync(ModDbDownload.ArcanePage); }
        catch (Exception error) { ActivityStore.Log(error); ShowToast(BrowserOpenError, true); }
        finally { _openingHelpLink = false; }
    }

    private async void ArcaneWarsDiscord_RequestNavigate(object sender, RequestNavigateEventArgs e)
    {
        e.Handled = true;
        await OpenArcaneWarsDiscordAsync(e.Uri);
    }

    private async Task OpenArcaneWarsDiscordAsync(Uri uri)
    {
        // Only this explicit, user-provided HTTPS invite may leave the app.
        // Never open arbitrary URIs from a feed/help body or a file:// address.
        if (_openingHelpLink || !uri.IsAbsoluteUri || uri.AbsoluteUri != ArcaneWarsDiscordInvite) return;
        _openingHelpLink = true;
        HelpLinkErrorText.Visibility = Visibility.Collapsed;
        ArcaneWarsDiscordLink.IsEnabled = false;
        try { await OpenConfirmedLinkAsync(ArcaneWarsDiscordInvite); }
        catch (Exception error)
        {
            ActivityStore.Log(error);
            HelpLinkErrorText.Text = BrowserOpenError();
            HelpLinkErrorText.Visibility = Visibility.Visible;
            ShowToast(BrowserOpenError, true);
        }
        finally { _openingHelpLink = false; ArcaneWarsDiscordLink.IsEnabled = true; }
    }
}
