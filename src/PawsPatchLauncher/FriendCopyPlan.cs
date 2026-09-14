namespace PawsPatchLauncher;

public enum FriendCopyAction { Apply, Install, Update, None }

public sealed record FriendCopyPlan(FriendCopyAction Action, bool Repair, int DownloadCount)
{
    public static bool MatchesApplied(SocialPlayer player, InstallState? state, SocialVersions? installed)
        => state?.AppliedSettings is { } applied && installed?.ContentId is { Length:64 } content
            && player.Versions is { } peer && content.Equals(peer.ContentId,StringComparison.OrdinalIgnoreCase) && peer.Mod==installed.Mod && peer.Channel==installed.Channel
            && peer.Patch==installed.Patch && FriendConfiguration.TryParse(player.Configuration,player.Channel,out var selection)
            && FriendConfiguration.Matches(selection,applied);
    // Compare the destination library entry, never the mod currently active in the game.
    public static FriendCopyPlan Create(ChannelManifest channel, UserSettings selection,
        ModLibraryEntry? installed, Func<PackageRelease, bool> locallyAvailable)
    {
        var packages = ModLibrary.Packages(channel, selection.Mod);
        var missing = packages.Where(p => !locallyAvailable(p)).ToList();
        var languages = GamePackageSelector.Select(channel, selection, selection.RussianLocalization, selection.CustomPlayerColors)
            .Where(GameLanguages.IsLanguage).Where(p => !locallyAvailable(p));
        var downloads = missing.Concat(languages).DistinctBy(p => p.Id).Count();
        if (installed is null || installed.Mod != selection.Mod || installed.Channel != selection.Channel)
            return new(FriendCopyAction.Install, false, downloads);
        if (!installed.ContentId.Equals(ModLibrary.ContentId(channel, selection.Mod), StringComparison.OrdinalIgnoreCase)
            && !installed.ContentId.Equals(ModLibrary.LegacyContentId(channel, selection.Mod), StringComparison.OrdinalIgnoreCase))
            return new(FriendCopyAction.Update, false, downloads);
        return missing.Count > 0 ? new(FriendCopyAction.Install, true, downloads) : new(FriendCopyAction.Apply, false, downloads);
    }
}
