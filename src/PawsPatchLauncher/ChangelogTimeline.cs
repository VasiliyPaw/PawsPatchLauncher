using System.Security.Cryptography;
using System.Text;

namespace PawsPatchLauncher;

public sealed record TimelineEntry(string Subject, string Source, string Branch, ChangelogEntry Entry, bool Overview = false)
{
    public string ContentId => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(string.Join("\n",
        Entry.Version, Entry.PublishedAt, Entry.Title.Ru, Entry.Title.En, Entry.Body.Ru, Entry.Body.En))));
    public string ReadKey => "timeline:2:" + Subject + ":" + Source + ":" + Branch + ":" + Entry.Version + ":" + Entry.PublishedAt + ":" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Entry.Title.Ru + "\n" + Entry.Title.En)))[..16];
}

public static class ChangelogTimeline
{
    public static IReadOnlyList<TimelineEntry> Entries(IEnumerable<ChannelManifest?> manifests, string subject, string source, string branch)
    {
        var feeds = manifests.Where(m => m is not null).Cast<ChannelManifest>()
            .GroupBy(m => m.Channel).Select(g => g.OrderByDescending(m => Date(m.PublishedAt)).First()).ToArray();
        var result = new List<TimelineEntry>();
        if (subject == "launcher")
        {
            foreach (var feed in feeds.OrderByDescending(m => Date(m.PublishedAt)))
                result.AddRange(ChangelogReadState.Entries(feed, "launcher", GameMod.Vanilla).Select(e => new TimelineEntry(subject, "launcher", "", e)));
        }
        else
        {
            GameMod.Validate(new UserSettings { Mod = subject });
            if (source is "all" or "patch")
                foreach (var feed in feeds.Where(m => branch == "all" || m.Channel == branch))
                {
                    var patch = ChangelogReadState.Entries(feed, "patch", subject).ToArray();
                    result.AddRange(patch.Select(e => new TimelineEntry(subject, "patch", feed.Channel, e)));
                    if (patch.Length == 0 && subject == GameMod.ArcaneWars && !string.IsNullOrWhiteSpace(feed.NewsBody.En + feed.NewsBody.Ru))
                        result.Add(new(subject, "patch", feed.Channel, new() { Title = feed.NewsTitle, Body = feed.NewsBody, PublishedAt = feed.PublishedAt }));
                }
            if (source is "all" or "mod")
            {
                foreach (var feed in feeds.OrderByDescending(m => Date(m.PublishedAt)))
                    result.AddRange(ChangelogReadState.Entries(feed, "mod", subject).Select(e => new TimelineEntry(subject, "mod", "", e)));
                // A guide describes an available version; it does not establish a publication date.
                if (subject != GameMod.Vanilla)
                {
                    var guide = feeds.OrderByDescending(m => Date(m.PublishedAt)).Select(m => GuideCatalog.Resolve(m, subject))
                        .FirstOrDefault(g => g is not null) ?? GuideCatalog.Resolve(null, subject);
                    if (guide is not null)
                    {
                        result.AddRange(GuideCatalog.ReleaseNotes(guide).Take(200).Select(e => new TimelineEntry(subject, "mod", "", e)));
                        result.Add(new(subject, "mod", "", new()
                        {
                            Version = guide.Version,
                            Title = new() { Ru = "Что входит в " + GameMod.Name(subject, true) + " " + guide.Version,
                                En = "What's included in " + GameMod.Name(subject, false) + " " + guide.Version },
                            Body = new() { Ru = guide.Description.Ru + "\n\n" + string.Join("\n\n", guide.Sections.Select(s => s.Title.Ru + "\n" + s.Body.Ru)),
                                En = guide.Description.En + "\n\n" + string.Join("\n\n", guide.Sections.Select(s => s.Title.En + "\n" + s.Body.En)) }
                        }, Overview: true));
                    }
                }
            }
        }
        return result.GroupBy(e => e.ReadKey + ":" + e.Overview).Select(g => g.First())
            .OrderBy(e => e.Overview).ThenByDescending(e => Date(e.Entry.PublishedAt))
            .ThenByDescending(e => VersionSort(e.Entry.Version), StringComparer.Ordinal).ToArray();
    }

    private static DateTimeOffset Date(string? value) => DateTimeOffset.TryParse(value, out var date) ? date : DateTimeOffset.MinValue;
    private static string VersionSort(string version) => System.Text.RegularExpressions.Regex.Replace(version, "[0-9]+", m => m.Value.PadLeft(12, '0'));

    public static bool IsUnread(UserSettings settings, TimelineEntry row)
    {
        if (row.Overview) return false;
        if (settings.ReadChangelogs.TryGetValue(row.ReadKey, out var seen)) return seen != row.ContentId;
        var legacy = row.Source == "launcher" ? "launcher" : row.Source == "patch"
            ? "patch:" + row.Branch + (row.Subject == GameMod.ArcaneWars ? "" : ":" + row.Subject) : "";
        return legacy.Length == 0 || !(settings.ReadChangelogs.GetValueOrDefault(legacy) ?? "")
            .Split('|').Contains(row.Entry.Version + ":" + row.Entry.PublishedAt, StringComparer.Ordinal);
    }

    public static bool MarkViewed(UserSettings settings, IEnumerable<TimelineEntry> rows, bool visible)
    {
        if (!visible) return false;
        var changed = false;
        foreach (var row in rows.Where(r => !r.Overview))
            if (settings.ReadChangelogs.GetValueOrDefault(row.ReadKey) != row.ContentId)
            { settings.ReadChangelogs[row.ReadKey] = row.ContentId; changed = true; }
        return changed;
    }
}
