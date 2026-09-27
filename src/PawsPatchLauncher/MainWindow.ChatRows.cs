using System.Windows;
using System.Windows.Controls;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private sealed record ChatRowState(SocialMessage? Message, PendingSocialMessage? Pending, SocialOffer? Offer, int MediaSlots);
    private sealed record ChatRow(ChatRowState? State, FrameworkElement Element);
    private readonly Dictionary<string, ChatRow> _messageRows = [];
    private string? _messageRowsAppearance;

    private void BeginChatRows(string appearance)
    {
        if (_messageRowsAppearance == appearance && _mediaOwner == _account.UserId) return;
        ResetChatMedia();
        _messageRowsAppearance = appearance;
        FriendsMessagesPanel.Children.Clear();
    }

    private FrameworkElement ChatDividerRow(string key, string text, bool unread)
    {
        key += "|" + text; // Yesterday/today labels can change while the chat stays open.
        if (!_messageRows.TryGetValue(key, out var row))
            _messageRows[key] = row = new(null, ChatDivider(text, unread));
        return row.Element;
    }

    private void RemoveChatRow(string key)
    {
        if (!_messageRows.Remove(key, out var row)) return;
        if (row.Element is Grid grid)
            foreach (var content in grid.Children.OfType<Border>().Select(b => b.Child).OfType<StackPanel>())
                ReleaseChatMedia(content);
    }

    private void ReconcileChatRows(List<FrameworkElement> rows)
    {
        var keep = rows.ToHashSet();
        foreach (var key in _messageRows.Where(p => !keep.Contains(p.Value.Element)).Select(p => p.Key).ToArray())
            RemoveChatRow(key);
        // Preserve controls that did not change, including selection and loaded GIFs.
        for (var i = FriendsMessagesPanel.Children.Count - 1; i >= 0; i--)
            if (!keep.Contains((FrameworkElement)FriendsMessagesPanel.Children[i])) FriendsMessagesPanel.Children.RemoveAt(i);
        for (var i = 0; i < rows.Count; i++)
        {
            if (i < FriendsMessagesPanel.Children.Count && ReferenceEquals(FriendsMessagesPanel.Children[i], rows[i])) continue;
            FriendsMessagesPanel.Children.Remove(rows[i]);
            FriendsMessagesPanel.Children.Insert(i, rows[i]);
        }
    }
}
