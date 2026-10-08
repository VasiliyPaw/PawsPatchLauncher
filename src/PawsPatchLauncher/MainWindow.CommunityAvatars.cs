using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;

namespace PawsPatchLauncher;

public partial class MainWindow
{
    private readonly Dictionary<Guid, (DateTimeOffset? Revision, ImageBrush? Image, DateTimeOffset Retry)> _communityAvatars = new();
    private readonly Dictionary<Guid, List<WeakReference<ContentControl>>> _communityAvatarViews = new();
    private readonly HashSet<Guid> _communityAvatarLoading = [];
    private bool _communityExtrasLoading;
    private int? _communityOnline;
    private DateTimeOffset _communityOnlineReceived;
    private Func<CancellationToken, Task<int>>? _communityOnlineOverride = null;
    private Func<Guid, DateTimeOffset, CancellationToken, Task<byte[]?>>? _communityAvatarOverride = null;

    private ContentControl CommunityAvatar(CommunityMessage message, double size)
    {
        var view = new ContentControl { Width = size, Height = size, Tag = message.AvatarRevision, IsHitTestVisible = false };
        if (!_communityAvatarViews.TryGetValue(message.SenderId, out var views)) _communityAvatarViews[message.SenderId] = views = [];
        views.RemoveAll(v => !v.TryGetTarget(out _));
        views.Add(new(view));
        var cached = _communityAvatars.GetValueOrDefault(message.SenderId);
        view.Content = CommunityAvatarVisual(size, cached.Revision == message.AvatarRevision ? cached.Image : null);
        return view;
    }

    private Grid CommunityAvatarVisual(double size, ImageBrush? photo)
    {
        var view = new Grid { Width = size, Height = size };
        view.Children.Add(new Ellipse { Fill = photo ?? (Brush)SocialBrush("#334C68"), Stroke = SocialBrush("#607A94"), StrokeThickness = 1 });
        if (photo is null) view.Children.Add(new LauncherIcon { Kind = IconKind.Person, Width = size*.58, Height = size*.58,
            HorizontalAlignment = HorizontalAlignment.Center, VerticalAlignment = VerticalAlignment.Center, Foreground = SocialBrush("#CCD7E4") });
        return view;
    }

    private async Task RefreshCommunityAvatarAsync(CommunityMessage message)
    {
        if (ActivityStore.IsSmokeTest && _communityAvatarOverride is null || message.AvatarRevision is not { } revision || _accountLifetime.IsCancellationRequested) return;
        var cached = _communityAvatars.GetValueOrDefault(message.SenderId);
        if (cached.Revision == revision && DateTimeOffset.UtcNow < cached.Retry || !_communityAvatarLoading.Add(message.SenderId)) return;
        try
        {
            var bytes = await (_communityAvatarOverride?.Invoke(message.SenderId, revision, _accountLifetime.Token)
                ?? _account.ReadCommunityAvatarAsync(message.SenderId, revision, _accountLifetime.Token));
            var image = bytes is null ? null : await Task.Run(() =>
            {
                var brush = new ImageBrush(AccountAvatarImage.Decode(bytes, normalized:true)) { Stretch = Stretch.UniformToFill };
                brush.Freeze(); return brush;
            });
            if (_accountLifetime.IsCancellationRequested) return;
            _communityAvatars[message.SenderId] = (revision, image, DateTimeOffset.UtcNow.AddMinutes(image is null ? 1 : 10));
            if (_communityAvatarViews.TryGetValue(message.SenderId, out var views))
                foreach (var weak in views)
                    if (weak.TryGetTarget(out var view) && Equals(view.Tag, revision)) view.Content = CommunityAvatarVisual(view.Width, image);
        }
        catch (Exception) { _communityAvatars[message.SenderId] = (revision, cached.Image, DateTimeOffset.UtcNow.AddMinutes(1)); }
        finally { _communityAvatarLoading.Remove(message.SenderId); }
    }

    private void RefreshCommunityOnline()
    {
        var current = _communityOnline is not null && DateTimeOffset.UtcNow - _communityOnlineReceived < TimeSpan.FromSeconds(90);
        CommunityDescription.Text = current ? T($"● {_communityOnline} в сети", $"● {_communityOnline} online") : T("● В сети: —", "● Online: —");
        CommunityDescription.Foreground = SocialBrush(current ? "#79C9A0" : "#A8BBD2");
        CommunityDescription.ToolTip = T("Пользователи, вошедшие в лаунчер. Гости не учитываются.", "Signed-in launcher users. Guests are not counted.");
    }

    private async Task RefreshCommunityExtrasAsync()
    {
        if (_communityExtrasLoading || _accountLifetime.IsCancellationRequested) return;
        _communityExtrasLoading = true;
        try
        {
            if (!ActivityStore.IsSmokeTest || _communityOnlineOverride is not null)
            {
                try { _communityOnline = await (_communityOnlineOverride?.Invoke(_accountLifetime.Token) ?? _account.ReadCommunityOnlineAsync(_accountLifetime.Token)); _communityOnlineReceived = DateTimeOffset.UtcNow; }
                catch (Exception) { _communityOnline = null; }
            }
            if (_accountLifetime.IsCancellationRequested) return;
            RefreshCommunityOnline();
            var visible = _communityViews[_communityChannel].Visible.Where(m => !m.Removed).DistinctBy(m => m.SenderId).ToArray();
            var keep = visible.Select(m => m.SenderId).ToHashSet();
            foreach (var id in _communityAvatars.Keys.Where(id => !keep.Contains(id)).ToArray()) _communityAvatars.Remove(id);
            foreach (var id in _communityAvatarViews.Keys.ToArray())
            {
                _communityAvatarViews[id].RemoveAll(v => !v.TryGetTarget(out _));
                if (_communityAvatarViews[id].Count == 0) _communityAvatarViews.Remove(id);
            }
            await Task.WhenAll(visible.Where(m => m.AvatarRevision is { } r && (!_communityAvatars.TryGetValue(m.SenderId, out var c) || c.Revision != r || c.Retry <= DateTimeOffset.UtcNow))
                .Take(4).Select(RefreshCommunityAvatarAsync));
        }
        finally { _communityExtrasLoading = false; }
    }
}
