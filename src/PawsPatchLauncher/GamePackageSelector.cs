namespace PawsPatchLauncher;

public static class GamePackageSelector
{
    // Shared by the UI and clean-install regression tests; preserves UI selection semantics.
    public static List<PackageRelease> Select(ChannelManifest channel, UserSettings settings, bool russianLocalization, bool customPlayerColors)
    {
        var ids = new HashSet<string>(channel.Packages.Where(x => x.Required).Select(x => x.Id), StringComparer.OrdinalIgnoreCase);
        if (russianLocalization) ids.Add("localization-ru");
        if (customPlayerColors) ids.Add("player-colors");
        if (settings.DesyncMode == "continue") ids.Add("desync-continue");
        var fastSpawn = settings.RoamingSpawnMode.Equals("x4", StringComparison.OrdinalIgnoreCase);
        if (!fastSpawn && settings.AdditionalRoamingCompanies) ids.Add("roaming-profile-standard-with-new");
        if (fastSpawn && !settings.AdditionalRoamingCompanies) ids.Add("roaming-profile-x4-no-new");
        if (!fastSpawn && !settings.AdditionalRoamingCompanies) ids.Add("roaming-profile-standard-no-new");
        if (!settings.SiegeBalance) ids.Add("siege-balance-standard");
        bool changed;
        do
        {
            changed = false;
            foreach (var package in channel.Packages.Where(x => ids.Contains(x.Id)))
                foreach (var dependency in package.DependsOn)
                    if (ids.Add(dependency)) changed = true;
        } while (changed);
        var missing = ids.Where(id => channel.Packages.All(x => !x.Id.Equals(id, StringComparison.OrdinalIgnoreCase))).ToList();
        if (missing.Count > 0) throw new InvalidDataException("Missing update packages: " + string.Join(", ", missing));
        return channel.Packages.Where(x => ids.Contains(x.Id)).ToList();
    }
}
