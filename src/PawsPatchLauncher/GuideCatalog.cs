using System.Text.Json;

namespace PawsPatchLauncher;

public static class GuideCatalog
{
    private static readonly Lazy<List<ModGuideDocument>> BuiltIn = new(() =>
    {
        using var stream = typeof(GuideCatalog).Assembly.GetManifestResourceStream("PawsPatchLauncher.Assets.mod-guides.json");
        return stream is null ? [] : JsonSerializer.Deserialize(stream, LauncherJsonContext.Default.ListModGuideDocument) ?? [];
    });

    public static ModGuideDocument? Resolve(ChannelManifest? channel, string mod)
        => channel?.ModGuides.FirstOrDefault(g => g.Id == mod && IsValid(g))
            ?? BuiltIn.Value.FirstOrDefault(g => g.Id == mod && IsValid(g));

    public static IEnumerable<ChangelogEntry> ReleaseNotes(ModGuideDocument document)
        => document.Changelog.Count > 0 ? document.Changelog
            : BuiltIn.Value.FirstOrDefault(g => g.Id == document.Id && g.Version == document.Version)?.Changelog ?? [];

    // These authored opening sections extend the short description. Present
    // them in the same card without changing signed or cached document data.
    // An unrelated first mechanic in a newer guide must keep its own card.
    public static ModGuideSection? IntroductionSection(ModGuideDocument document)
    {
        var expected = document.Id switch
        {
            GameMod.Vanilla => "original", GameMod.ArcaneWars => "overview",
            GameMod.Immortals => "approach", _ => ""
        };
        return document.Sections.FirstOrDefault() is { } first && first.Id == expected ? first : null;
    }

    public static bool IsValid(ModGuideDocument? document)
        => document is { Id: GameMod.Vanilla or GameMod.ArcaneWars or GameMod.Immortals,
            Version.Length: > 0 and <= 80, Author.Length: <= 200, Sections.Count: > 0 and <= 200 }
        && document.Changelog is { Count: <= 200 }
        && document.Changelog.All(e => e is not null && e.Version is { Length: <= 80 } && e.PublishedAt is { Length: <= 80 }
            && ValidText(e.Title, 200) && ValidText(e.Body, 40000))
        && ValidText(document.Description, 16000)
        && document.Sections.All(s => s is not null && s.Id is { Length: > 0 and <= 80 }
            && s.Id.All(c => char.IsAsciiLetterOrDigit(c) || c == '-')
            && ValidText(s.Title, 200) && ValidText(s.Body, 40000))
        && document.Sections.Select(s => s.Id).Distinct(StringComparer.Ordinal).Count() == document.Sections.Count;

    private static bool ValidText(LocalizedText? text, int max)
        => text is not null && !string.IsNullOrWhiteSpace(text.Ru) && !string.IsNullOrWhiteSpace(text.En)
            && text.Ru.Length <= max && text.En.Length <= max;
}
