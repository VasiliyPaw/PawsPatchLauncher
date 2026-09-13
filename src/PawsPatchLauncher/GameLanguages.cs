namespace PawsPatchLauncher;

public static class GameLanguages
{
    public static ChannelManifest SelectionCatalog(ChannelManifest installed, ChannelManifest? offered, UserSettings selection)
        => selection.PinnedRelease is null && offered is not null && installed.Channel == offered.Channel
            && !ModLibrary.HasUpdate(installed, offered, selection.Mod) ? offered : installed;

    // Older profiles coupled speech to text. A missing value preserves that choice.
    public static string Voice(UserSettings settings) => settings.GameVoiceLanguage is "en" or "ru"
        ? settings.GameVoiceLanguage : settings.RussianLocalization ? "ru" : "en";
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
