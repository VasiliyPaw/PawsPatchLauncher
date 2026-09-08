using System.Diagnostics;
using System.Windows;
using System.Windows.Navigation;

namespace PawsPatchLauncher;

public partial class MainWindow
{
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
        ArcaneWarsCreditPanel.Visibility = helpKey == "modules.core" ? Visibility.Visible : Visibility.Collapsed;
        ArcaneWarsAuthorLabel.Text = T("Автор Arcane Wars: ", "Arcane Wars author: ");
        ArcaneWarsDistributionText.Text = T("Автор распространяет мод на этом Discord-сервере.",
            "The author distributes the mod on this Discord server.");
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
        try { await _openHelpLink(ArcaneWarsDiscordInvite); }
        catch (Exception error)
        {
            ActivityStore.Log(error);
            HelpLinkErrorText.Text = T("Не удалось открыть браузер. Попробуйте ещё раз или откройте ссылку вручную.",
                "Could not open the browser. Try again or open the link manually.");
            HelpLinkErrorText.Visibility = Visibility.Visible;
        }
        finally { _openingHelpLink = false; ArcaneWarsDiscordLink.IsEnabled = true; }
    }
}
