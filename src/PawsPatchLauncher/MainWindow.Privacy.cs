using System.Windows;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private const string PrivacyPolicyUrl = "https://github.com/VasiliyPaw/PawsPatchLauncher/blob/main/docs/PRIVACY.md";

    private async void PrivacyPolicy_Click(object sender, RoutedEventArgs e)
    {
        try { await _openHelpLink(PrivacyPolicyUrl); }
        catch { ShowToast(() => T("Не удалось открыть политику конфиденциальности в браузере.", "Could not open the privacy policy in your browser."), true); }
    }
}
