namespace PawsPatchLauncher;

public static class RebornHistory
{
    public const int Limit = 200;
    public static IReadOnlyList<TimelineEntry> Entries(IEnumerable<RebornBuild> builds, string branch, string language)
        => builds.Where(b => branch == "all" || b.Channel == branch).OrderByDescending(b => b.PublishedAt).ThenByDescending(b => b.Id)
            .Select(b => new TimelineEntry("reborn", "reborn", b.Channel, new ChangelogEntry
            {
                Category = "reborn", Version = b.Version, PublishedAt = b.PublishedAt.ToString("O"),
                Title = new() { Ru = "Kohan Reborn", En = "Kohan Reborn" },
                Body = new() { Ru = b.Note("ru"), En = b.Note("en") }
            }) { LocalizedBody = b.Note(language), Revision = b.Id + "\n" + System.Text.Json.JsonSerializer.Serialize(b.Notes.OrderBy(n => n.Key)) }).ToArray();
}
