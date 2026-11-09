namespace PawsPatchLauncher;

public static class GameplayComparison
{
    public static IReadOnlyList<ConfigurationChange> Differences(UserSettings local, UserSettings peer, string language)
    {
        // Canonical wire configurations remove personal languages and inactive options.
        return ConfigurationChanges.Compare(ConfigurationCode.Parse(FriendConfiguration.Create(local)),
            ConfigurationCode.Parse(FriendConfiguration.Create(peer)), language);
    }
}
