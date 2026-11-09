using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private void CustomVoices_Click(object sender, RoutedEventArgs e)
    {
        if (_busy || ConfirmationActive || !CanChooseSeparateVoice) return;
        CreateCustomVoicesDialog().ShowDialog();
    }

    private Window CreateCustomVoicesDialog()
    {
        var (window, host) = CreateCommunityDialog(T("Пользовательская озвучка", "Custom speech"), IconKind.Language, 590, 690);
        window.MinHeight = 440;
        var body = new StackPanel();
        body.Children.Add(new TextBlock { Text = T("Выберите язык для каждой фракции. Текст игры останется прежним.",
            "Choose a language for each faction. Game text stays unchanged."), Foreground = SocialBrush("#A8BBD2"), TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 16) });
        var choices = new Dictionary<string, ComboBox>();
        foreach (var group in CustomVoices.Groups)
        {
            var row = new Grid { Margin = new Thickness(14, 11, 14, 11) };
            row.ColumnDefinitions.Add(new ColumnDefinition());
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(205) });
            row.Children.Add(new TextBlock { Text = CustomVoices.Label(group, _text.Language), FontSize = 14, FontWeight = FontWeights.SemiBold,
                TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 12, 0), VerticalAlignment = VerticalAlignment.Center });
            var combo = new ComboBox { Name = "CustomVoice_" + group, Style = (Style)FindResource("ReleaseCombo"), DisplayMemberPath = "Label",
                ItemsSource = GameLanguages.VoiceChoices.Select(code => new LanguageChoice(code, UiLanguages.GameLanguageName(code, _text.Language))).ToArray() };
            combo.SelectedItem = ((IEnumerable<LanguageChoice>)combo.ItemsSource).First(c => c.Code == CustomVoices.Language(_settings, group));
            System.Windows.Automation.AutomationProperties.SetName(combo, CustomVoices.Label(group, _text.Language));
            Grid.SetColumn(combo, 1); row.Children.Add(combo); choices[group] = combo;
            body.Children.Add(new Border { Background = SocialBrush("#142B44"), BorderBrush = SocialBrush("#2D4561"), BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(8), Margin = new Thickness(0, 0, 0, 8), Child = row });
        }
        body.Children.Add(new TextBlock { Text = T("Язык определяется фракцией владельца отряда, а не расой. Например, люди Роялистов и Совета могут говорить по-разному. Герои используют язык своего владельца.",
            "Speech follows the unit owner's faction, not its race. For example, Royalist and Council humans can speak different languages. Heroes use their owner's language."),
            TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush("#A8BBD2"), FontSize = 12, Margin = new Thickness(0, 6, 0, 12) });
        body.Children.Add(new Border { Background = SocialBrush("#25352F"), CornerRadius = new CornerRadius(8), Padding = new Thickness(12),
            Child = new TextBlock { Text = T("Набор сохранится при переключении на обычную озвучку. Для разных языков фракций нужна Kohan II 1.3.72. Примените настройки и запускайте игру через этот лаунчер.",
                "Your setup is kept when you switch to regular speech. Different faction languages require Kohan II 1.3.72. Apply settings and start the game through this launcher."),
                TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush("#A8D6BC"), FontSize = 12 } });
        var actions = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 18, 0, 0) };
        var cancel = new Button { Content = T("Отмена", "Cancel"), Style = (Style)FindResource("GhostButton"), Margin = new Thickness(0, 0, 8, 0) };
        cancel.Click += (_, _) => window.Close(); actions.Children.Add(cancel);
        var save = new Button { Name = "SaveCustomVoices", Content = T("Сохранить", "Save"), Style = (Style)FindResource("GoldButton") };
        save.Click += (_, _) =>
        {
            if (_busy || ConfirmationActive) return;
            _settings.FactionVoiceLanguages = choices.ToDictionary(p => p.Key, p => ((LanguageChoice)p.Value.SelectedItem).Code);
            _settingsStore.Save(_settings); SyncLanguageChoices(); RefreshLanguageSelection(); window.Close();
        };
        actions.Children.Add(save);
        var layout = new Grid(); layout.RowDefinitions.Add(new RowDefinition()); layout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        layout.Children.Add(new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled });
        Grid.SetRow(actions, 1); layout.Children.Add(actions); host.Content = layout;
        return window;
    }
}
