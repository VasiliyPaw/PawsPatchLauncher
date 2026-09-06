using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private bool _syncingPatchChannel;

    private void SyncPatchChannelControls()
    {
        _syncingPatchChannel = true;
        try
        {
            var beta = _settings.Channel.Equals("beta", StringComparison.OrdinalIgnoreCase);
            HeaderReleaseRadio.IsChecked = SettingsReleaseRadio.IsChecked = !beta;
            HeaderBetaRadio.IsChecked = SettingsBetaRadio.IsChecked = beta;
            foreach (var control in new[] { HeaderReleaseRadio, HeaderBetaRadio, SettingsReleaseRadio, SettingsBetaRadio })
                control.IsEnabled = !_busy && !_checkingFeed;
        }
        finally { _syncingPatchChannel = false; }
    }

    private void ApplyPatchChannelLanguage()
    {
        PatchChannelLabel.Text = _text["patch.channel"];
        PatchUpdatesTitleText.Text = _text["patch.updates"];
        PatchChannelDescriptionText.Text = _text["patch.channel.help"];
        LauncherUpdatesDescriptionText.Text = _text["launcher.updates.help"];
        HeaderReleaseRadio.Content = SettingsReleaseRadio.Content = ChannelPresentation.Name("stable", _text.Language);
        HeaderBetaRadio.Content = SettingsBetaRadio.Content = ChannelPresentation.Name("beta", _text.Language);
        foreach (var control in new[] { HeaderReleaseRadio, HeaderBetaRadio, SettingsReleaseRadio, SettingsBetaRadio })
        {
            control.ToolTip = _text[control.Tag as string == "beta" ? "patch.beta.tip" : "patch.release.tip"];
            System.Windows.Automation.AutomationProperties.SetName(control, _text["patch.channel"] + " " + control.Content);
        }
        SyncPatchChannelControls();
    }

    private async void PatchChannel_Checked(object sender, RoutedEventArgs e)
    {
        if (_syncingPatchChannel || _initializing || sender is not RadioButton { Tag: string channel }) return;
        await ChangeChannelAsync(channel == "beta");
    }
}
