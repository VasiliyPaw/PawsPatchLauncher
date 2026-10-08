using System.Text.Json;

namespace PawsPatchLauncher;

public sealed record CommunityMessage(long Ordinal, Guid Id, Guid SenderId, string Nickname,
    string DisplayName, string Body, DateTimeOffset CreatedAt, bool Removed, int AdminLevel);

public sealed record CommunityPage(IReadOnlyList<CommunityMessage> Messages, bool More, long Revision, bool Trimmed);

// Keep data separate from the bounded WPF window. Reading thousands of older
// messages never creates thousands of controls, and polling retains row identity.
public class CommunityHistory
{
    public const int PageSize = 100, VisibleLimit = 200;
    public IReadOnlyList<CommunityMessage> Messages = [];
    public int ViewStart;
    public long Revision = -1;
    public bool More, Trimmed, Loaded;
    private CommunityPage? _latestPage;
    public bool AtNewest => ViewStart + VisibleLimit >= Messages.Count;
    public IEnumerable<CommunityMessage> Visible => Messages.Skip(ViewStart).Take(VisibleLimit);
    public bool Merge(CommunityPage page, bool older, bool follow)
    {
        if (page.Revision < Revision || older && page.Revision != Revision) return false;
        if (!older && _latestPage is { } latest && latest.Revision == page.Revision && latest.More == page.More
            && latest.Trimmed == page.Trimmed && latest.Messages.SequenceEqual(page.Messages)) return true;
        var reset = page.Revision != Revision;
        // Never stitch disjoint windows across an offline gap.
        var known = Messages.Select(m => m.Ordinal).ToHashSet();
        reset |= !older && page.Messages.Count == PageSize && Messages.Count > 0 && !page.Messages.Any(m => known.Contains(m.Ordinal));
        var first = Messages.Count == 0;
        var anchor = Messages.ElementAtOrDefault(ViewStart)?.Ordinal;
        var merged = (reset ? [] : Messages).Concat(page.Messages).GroupBy(m => m.Ordinal).Select(g => g.Last())
            .OrderBy(m => m.Ordinal).TakeLast(10000).ToArray();
        if (!Messages.SequenceEqual(merged)) Messages = merged;
        Revision = page.Revision; Trimmed = page.Trimmed; Loaded = true;
        if (!older) _latestPage = page;
        if (older || reset || first) More = page.More;
        var anchorIndex = anchor is null ? 0 : Array.FindIndex(merged, m => m.Ordinal == anchor);
        ViewStart = reset || first || follow ? Math.Max(0, Messages.Count - VisibleLimit)
            : Math.Clamp(anchorIndex - (older ? PageSize : 0), 0, Math.Max(0, Messages.Count - VisibleLimit));
        return true;
    }
    public void Append(CommunityMessage message)
    {
        Messages = Messages.Where(m => m.Id != message.Id).Append(message).OrderBy(m => m.Ordinal).TakeLast(10000).ToArray();
        ViewStart = Math.Max(0, Messages.Count - VisibleLimit); Loaded = true;
    }
}

public static class CommunityChat
{
    public static bool Mentions(string body, string nickname) => !string.IsNullOrWhiteSpace(nickname)
        && System.Text.RegularExpressions.Regex.IsMatch(body,
            @"(?<![\p{L}\p{N}_@.\-])@" + System.Text.RegularExpressions.Regex.Escape(nickname) + @"(?![\p{L}\p{N}_\-]|\.[\p{L}\p{N}_])",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase | System.Text.RegularExpressions.RegexOptions.CultureInvariant);
    public const int MessageLimit = 1000;
    public static void ValidateChannel(string channel)
    { if (channel is not ("ru" or "en")) throw new AccountException("invalid_message"); }
    public static void Validate(string body)
    {
        if (string.IsNullOrWhiteSpace(body) || body.EnumerateRunes().Count() > MessageLimit
            || body.Any(c => char.IsControl(c) && c is not ('\r' or '\n' or '\t')))
            throw new AccountException("invalid_message");
    }
    // Persist the user's desired DIP width, not the temporarily clamped width on
    // a smaller display. Zero means the original wide layout on first use.
    public static double Width(double available, double saved)
    {
        if (!double.IsFinite(available) || available <= 0) return 0;
        var maximum = Math.Max(180, Math.Min(620, available - 470));
        var minimum = Math.Min(290, maximum);
        var desired = double.IsFinite(saved) && saved > 0 ? saved : available * .35;
        return Math.Clamp(desired, minimum, maximum);
    }
    public static CommunityMessage Read(JsonElement p)
    {
        try
        {
            var value = new CommunityMessage(p.GetProperty("ordinal").GetInt64(), p.GetProperty("message_id").GetGuid(),
                p.GetProperty("sender_id").GetGuid(), p.GetProperty("nickname").GetString()!, p.GetProperty("display_name").GetString()!,
                p.GetProperty("body").GetString()!, p.GetProperty("created_at").GetDateTimeOffset(),
                p.GetProperty("removed").GetBoolean(), p.GetProperty("admin_level").GetInt32());
            if (value.Ordinal <= 0 || value.Id == Guid.Empty || value.SenderId == Guid.Empty || value.AdminLevel is < 0 or > 10)
                throw new AccountException("invalid_response");
            if (value.Nickname is null || value.DisplayName is null || value.Body is null) throw new AccountException("invalid_response");
            AccountService.ValidateNickname(value.Nickname); AccountService.ValidateDisplayName(value.DisplayName);
            if (value.Removed) { if (value.Body != "") throw new AccountException("invalid_response"); }
            else Validate(value.Body);
            return value;
        }
        catch (Exception e) when (e is JsonException or InvalidOperationException or KeyNotFoundException or FormatException or AccountException)
        { throw new AccountException("invalid_response"); }
    }
}

// Per-owner/channel high-water marks prevent sounds for initial history, paging,
// edits, removals and repeated polls. Muting still advances the baseline.
public sealed class CommunityNotificationTracker
{
    private string _owner = "";
    private readonly Dictionary<string, long> _last = new();
    public bool Observe(string channel, IReadOnlyList<CommunityMessage> messages, string owner, string nickname, string mode)
    {
        if (_owner != owner) { _owner = owner; _last.Clear(); }
        var top = messages.LastOrDefault()?.Ordinal ?? 0;
        var known = _last.TryGetValue(channel, out var previous);
        _last[channel] = Math.Max(previous, top);
        if (!known || !Guid.TryParse(owner, out var id) || mode == "mute") return false;
        return messages.Any(m => m.Ordinal > previous && m.SenderId != id && !m.Removed
            && (mode == "all" || CommunityChat.Mentions(m.Body, nickname)));
    }
}
