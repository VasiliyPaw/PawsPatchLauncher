using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private sealed record LanguageChoice(string Code, string Label)
    {
        public override string ToString() => Label;
    }
    private bool _syncingLanguages;
    private string? _choiceLanguage;
    private bool CanChooseSeparateVoice => GameLanguages.SupportsSeparateVoice(_channel)
        || _settings.PinnedRelease is null && _offeredModChannel?.Channel == _settings.Channel && GameLanguages.SupportsSeparateVoice(_offeredModChannel);
    private void RefreshLanguageSelection()
    {
        if (_initializing || _syncingLanguages || _busy) return;
        // SelectionChanged already contains the final choice. Closing an unchanged
        // dropdown must not repeat the installation/process checks or restart fades.
        InvalidateReadiness();
        RefreshStatus();
    }

    private void InitializeLanguageChoices()
    {
        LauncherLanguageCombo.ItemsSource = UiLanguages.Choices.Select(c => new LanguageChoice(c.Code, c.Label)).ToArray();
        SyncLanguageChoices();
    }

    private void SyncLanguageChoices()
    {
        _syncingLanguages = true;
        try
        {
            if (_choiceLanguage != _text.Language)
            {
                _choiceLanguage = _text.Language;
                GameLanguageCombo.ItemsSource = new[] { "en", "ru" }.Select(code => new LanguageChoice(code, UiLanguages.GameLanguageName(code, _text.Language))).ToArray();
                GameVoiceCombo.ItemsSource = new[] { "en", "ru" }.Select(code => new LanguageChoice(code, UiLanguages.GameLanguageName(code, _text.Language))).ToArray();
            }
            if (GameLanguageCombo.ItemsSource is IEnumerable<LanguageChoice> gameLanguages)
                GameLanguageCombo.SelectedItem = gameLanguages.First(x => x.Code == (_settings.RussianLocalization ? "ru" : "en"));
            if (LauncherLanguageCombo.ItemsSource is IEnumerable<LanguageChoice> launcherLanguages)
                LauncherLanguageCombo.SelectedItem = launcherLanguages.First(x => x.Code == _text.Language);
            if (GameVoiceCombo.ItemsSource is IEnumerable<LanguageChoice> voices)
                GameVoiceCombo.SelectedItem = voices.First(x => x.Code == GameLanguages.Voice(_settings));
            GameTextLabel.Text = T("Текст", "Text");
            GameVoiceLabel.Text = T("Озвучка", "Speech");
            GameVoiceCombo.IsEnabled = !_busy && CanChooseSeparateVoice;
            GameVoiceCombo.ToolTip = GameLanguages.SupportsSeparateVoice(_channel) ? null : CanChooseSeparateVoice
                ? T("Для раздельного выбора текста и озвучки потребуется обновить файлы мода.", "Separate text and speech choices will require updating the mod files.")
                : T("Отдельный выбор озвучки появится после обновления файлов режима.", "Separate speech selection requires updated mode files.");
            System.Windows.Automation.AutomationProperties.SetName(GameVoiceCombo, T("Язык озвучки", "Speech language"));
            RussianToggle.IsChecked = _settings.RussianLocalization;
            GameLanguageCombo.IsEnabled = !_busy;
            System.Windows.Automation.AutomationProperties.SetName(GameLanguageCombo, T("Язык игры", "Game language"));
            System.Windows.Automation.AutomationProperties.SetName(LauncherLanguageCombo, T("Язык лаунчера", "Launcher language"));
        }
        finally { _syncingLanguages = false; }
    }

    private void GameLanguage_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (_initializing || _syncingLanguages || GameLanguageCombo.SelectedItem is not LanguageChoice language) return;
        if (_busy || ConfirmationActive) { SyncLanguageChoices(); return; }
        if (_settings.RussianLocalization == (language.Code == "ru")) return;
        _settings.GameVoiceLanguage = CanChooseSeparateVoice ? GameLanguages.Voice(_settings) : language.Code;
        _settings.RussianLocalization = language.Code == "ru";
        RussianToggle.IsChecked = _settings.RussianLocalization;
        _settingsStore.Save(_settings);
        RefreshLanguageSelection();
    }

    private void GameVoice_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (_initializing || _syncingLanguages || GameVoiceCombo.SelectedItem is not LanguageChoice language) return;
        if (_busy || ConfirmationActive) { SyncLanguageChoices(); return; }
        if (GameLanguages.Voice(_settings) == language.Code) return;
        _settings.GameVoiceLanguage = language.Code;
        _settingsStore.Save(_settings);
        RefreshLanguageSelection();
    }

    private void LauncherLanguage_Changed(object sender, SelectionChangedEventArgs e)
    {
        if (_initializing || _syncingLanguages || LauncherLanguageCombo.SelectedItem is not LanguageChoice language || language.Code == _text.Language) return;
        _settings.Language = language.Code;
        _text.SetLanguage(language.Code);
        _settingsStore.Save(_settings); ApplyLanguage();
    }

    private static void RevealDialogCard(FrameworkElement card)
    {
        Motion.Reveal(card);
        if (!SystemParameters.ClientAreaAnimation) return;
        var transform = new TranslateTransform();
        card.RenderTransform = transform;
        transform.BeginAnimation(TranslateTransform.YProperty, new DoubleAnimation(12, 0, TimeSpan.FromMilliseconds(220))
        { EasingFunction = new CubicEase { EasingMode = EasingMode.EaseOut } });
    }
}
