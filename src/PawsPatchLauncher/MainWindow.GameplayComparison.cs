using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private void CompareProfile_Click(object sender, RoutedEventArgs e)
    {
        if (ConfirmationActive || SocialDetailsPlayer() is not { } player) return;
        CreateGameplayComparisonDialog(player)?.Show();
    }

    private Window? CreateGameplayComparisonDialog(SocialPlayer player)
    {
        if (!FriendConfiguration.TryParse(player.Configuration, player.Channel, out var peer)) return null;
        var changes = GameplayComparison.Differences(LocalAppliedConfiguration(), peer, _text.Language);
        var body = new StackPanel { Margin = new Thickness(24) };
        body.Children.Add(new TextBlock { Text = T("Перед совместной игрой", "Before playing together"), FontSize = 22, FontWeight = FontWeights.SemiBold });
        body.Children.Add(new TextBlock { Text = player.Name + " · @" + player.Nickname, Foreground = SocialBrush("#A8BBD2"), Margin = new Thickness(0, 8, 0, 18) });
        body.Children.Add(new Border { Background = SocialBrush(changes.Count == 0 ? "#193B36" : "#403A28"), CornerRadius = new CornerRadius(9), Padding = new Thickness(14), Margin = new Thickness(0, 0, 0, 18),
            Child = new TextBlock { Text = changes.Count == 0 ? T("Опубликованные игровые настройки совпадают", "Published gameplay settings match")
                : T("Различий в игровых настройках: ", "Gameplay setting differences: ") + changes.Count, TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush(changes.Count == 0 ? "#83DEB8" : "#EAC978") } });
        Grid Row(string label, string local, string theirs, bool header)
        {
            var row = new Grid { Margin = new Thickness(0, 0, 0, 8) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
            row.ColumnDefinitions.Add(new ColumnDefinition()); row.ColumnDefinitions.Add(new ColumnDefinition());
            foreach (var (column, text) in new[] { (0, label), (1, local), (2, theirs) })
            {
                var cell = new Border { Padding = new Thickness(10), Background = header ? Brushes.Transparent : SocialBrush(column == 2 ? "#3B3628" : "#1B334B"), CornerRadius = new CornerRadius(6), Margin = new Thickness(0, 0, 5, 0),
                    Child = new TextBlock { Text = text, TextWrapping = TextWrapping.Wrap, FontSize = header ? 11 : 13, Foreground = SocialBrush(header ? "#A8BBD2" : column == 2 ? "#EAC978" : "#E7EFF8"), VerticalAlignment = VerticalAlignment.Center } };
                Grid.SetColumn(cell, column); row.Children.Add(cell);
            }
            return row;
        }
        body.Children.Add(Row(T("ТОЛЬКО РАЗЛИЧИЯ", "DIFFERENCES ONLY"), T("У вас", "You"), T("У игрока", "Player"), true));
        foreach (var change in changes) body.Children.Add(Row(change.Name, change.Before, change.After, false));
        var version = FriendVersionStatus(player);
        body.Children.Add(new TextBlock { Text = version == PeerVersionStatus.Current ? T("Версии лаунчера и патча совпадают.", "Launcher and patch versions match.")
            : version is PeerVersionStatus.Unknown or PeerVersionStatus.Checking ? T("Версии лаунчера и патча пока не подтверждены. Показано сравнение настроек.", "Launcher and patch versions are not confirmed yet. Gameplay settings are compared below.") : FriendVersionWarning(version),
            TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush(version == PeerVersionStatus.Current ? "#83DEB8" : "#EAC978"), Margin = new Thickness(0, 12, 0, 0) });
        body.Children.Add(new TextBlock { Text = T("Язык текста и озвучки не мешает совместной игре и не включён в различия. Сравнение настроек не заменяет проверку файлов игры.",
            "Text and speech languages are excluded from gameplay differences. Comparing settings does not replace verification of game files."), TextWrapping = TextWrapping.Wrap, Foreground = SocialBrush("#A8BBD2"), FontSize = 12, Margin = new Thickness(0, 14, 0, 0) });
        return new Window { Owner = IsLoaded ? this : null, Title = T("Сравнение с игроком", "Compare with player"), FontFamily = new FontFamily("Arial"),
            Width = Math.Min(680, SystemParameters.WorkArea.Width - 32), MaxHeight = SystemParameters.WorkArea.Height - 40, SizeToContent = SizeToContent.Height,
            WindowStartupLocation = WindowStartupLocation.CenterOwner, Background = SocialBrush("#102238"), Content = new ScrollViewer { Content = body, VerticalScrollBarVisibility = ScrollBarVisibility.Auto } };
    }
}
