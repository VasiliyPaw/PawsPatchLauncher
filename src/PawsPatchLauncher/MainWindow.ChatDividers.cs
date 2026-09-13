using System.Globalization;
using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly ChatUnreadDivider _chatUnreadDivider = new();

    private Guid? ChatUnreadBoundary()
    {
        if (_activePage != "friends" || _socialSection != "chats" || _socialPeer is not Guid peer
            || !Guid.TryParse(_account.UserId, out var owner)
            || _socialPlayers.FirstOrDefault(p => p.Id == peer) is not { } player)
        { _chatUnreadDivider.End(); return null; }
        _chatUnreadDivider.Begin(owner, player);
        // The cached tail may precede all unread messages reported by the friends poll.
        if (_chatAwaitingLatest) return null;
        return _chatUnreadDivider.Boundary(_socialMessages);
    }

    private FrameworkElement ChatDivider(string text, bool unread)
    {
        var row = new Grid { Margin = new Thickness(0, 8, 0, 14), Tag = unread ? "chat-new-divider" : "chat-date-divider", IsHitTestVisible = false };
        row.ColumnDefinitions.Add(new ColumnDefinition());
        row.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        if (!unread) row.ColumnDefinitions.Add(new ColumnDefinition());
        var brush = SocialBrush(unread ? "#E26573" : "#465B73");
        row.Children.Add(new Border { Height = 1, Background = brush, VerticalAlignment = VerticalAlignment.Center });
        var label = new TextBlock { Text = text, FontSize = unread ? 10 : 11, FontWeight = FontWeights.SemiBold,
            Foreground = SocialBrush(unread ? "#FFFFFF" : "#B4C8DC"), VerticalAlignment = VerticalAlignment.Center };
        var badge = new Border { Child = label, Padding = new Thickness(unread ? 6 : 9, unread ? 2 : 0, unread ? 6 : 9, unread ? 2 : 0),
            Background = unread ? brush : null, CornerRadius = new CornerRadius(4) };
        Grid.SetColumn(badge, 1); row.Children.Add(badge);
        if (!unread)
        {
            var line = new Border { Height = 1, Background = brush, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(line, 2); row.Children.Add(line);
        }
        return row;
    }

    private string ChatDay(DateTime date) => date.ToString(_text.Language == "ru" ? "d MMMM yyyy 'г.'" : "MMMM d, yyyy",
        CultureInfo.GetCultureInfo(_text.Language == "ru" ? "ru-RU" : "en-US"));
}
