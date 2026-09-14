namespace PawsPatchLauncher;

public static class GameLanguages
{
    public static ChannelManifest SelectionCatalog(ChannelManifest installed, ChannelManifest? offered, UserSettings selection)
        => selection.PinnedRelease is null && offered is not null && installed.Channel == offered.Channel
            && !ModLibrary.HasUpdate(installed, offered, selection.Mod) ? offered : installed;

    public static IReadOnlyList<string> Choices { get; } = ["en", "ru", "de", "fr"];
    // Keep the old Russian flag readable in saved profiles and configuration codes.
    public static string Text(UserSettings settings) => settings.GameTextLanguage ?? (settings.RussianLocalization ? "ru" : "en");
    public static void SetText(UserSettings settings, string language)
    {
        if (!Choices.Contains(language)) throw new InvalidDataException("Unsupported text language.");
        settings.GameTextLanguage = language is "de" or "fr" ? language : null;
        settings.RussianLocalization = language == "ru";
    }
    // Older profiles coupled speech to text. A missing value preserves that choice.
    public static string Voice(UserSettings settings) => settings.GameVoiceLanguage ?? Text(settings);
    public static bool SupportsSeparateVoice(ChannelManifest? channel) => channel?.Packages.Any(p => p.Id == "game-voice-ru") == true;
    public static bool IsLanguage(PackageRelease package) => package.Id.Contains("localization-", StringComparison.OrdinalIgnoreCase)
        || package.Id.StartsWith("game-voice-", StringComparison.OrdinalIgnoreCase) || package.Id == "pawpatch-data-ru";

    public static bool HasUpdate(ChannelManifest installed, ChannelManifest offered, UserSettings applied)
    {
        var before = GamePackageSelector.Select(installed, applied, applied.RussianLocalization, applied.CustomPlayerColors)
            .Where(IsLanguage).Select(p => p.Id + ":" + p.Version + ":" + p.Sha256).Order().ToArray();
        var after = GamePackageSelector.Select(offered, applied, applied.RussianLocalization, applied.CustomPlayerColors)
            .Where(IsLanguage).Select(p => p.Id + ":" + p.Version + ":" + p.Sha256).Order().ToArray();
        return !before.SequenceEqual(after, StringComparer.OrdinalIgnoreCase);
    }
}
