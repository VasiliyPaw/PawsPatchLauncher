namespace PawsPatchLauncher;

public static class CustomVoices
{
    // Stable order is also used by the local configuration-code suffix.
    public static IReadOnlyList<string> Groups { get; } = ["royalist", "council", "nationalist", "ceyah", "fallen", "other"];
    public static string Language(UserSettings settings, string group)
        => settings.FactionVoiceLanguages.TryGetValue(group, out var language) ? language : "en";
    public static Dictionary<string, string> Copy(UserSettings settings)
        => new(settings.FactionVoiceLanguages, StringComparer.Ordinal);
    public static void Initialize(UserSettings settings, string language)
    {
        if (settings.FactionVoiceLanguages.Count != 0) return;
        foreach (var group in Groups) settings.FactionVoiceLanguages[group] = language;
    }
    public static void Validate(UserSettings settings)
    {
        if (settings.FactionVoiceLanguages is null || settings.FactionVoiceLanguages.Count > Groups.Count
            || settings.FactionVoiceLanguages.Any(p => !Groups.Contains(p.Key) || !GameLanguages.VoiceChoices.Contains(p.Value)))
            throw new InvalidDataException("Invalid custom speech settings.");
    }
    public static string Signature(UserSettings settings) => GameLanguages.Voice(settings) == "custom"
        ? "custom:" + string.Join(',', Groups.Select(g => Language(settings, g))) : GameLanguages.Voice(settings);
    public static IEnumerable<string> SelectedLanguages(UserSettings settings) => GameLanguages.Voice(settings) == "custom"
        ? GameLanguages.VoiceChoices : [GameLanguages.Voice(settings)];
    public static string Label(string group, string language) => group switch
    {
        "royalist" => UiLanguages.Text(language, "Роялисты", "Royalist"),
        "council" => UiLanguages.Text(language, "Совет", "Council"),
        "nationalist" => UiLanguages.Text(language, "Националисты", "Nationalist"),
        "ceyah" => UiLanguages.Text(language, "Сейя", "Ceyah"),
        "fallen" => UiLanguages.Text(language, "Падшие", "Fallen"),
        "other" => UiLanguages.Text(language, "Кампания и нейтральные", "Campaign and neutrals"),
        _ => throw new ArgumentOutOfRangeException(nameof(group))
    };
    // Shipped game helpers exclude game-voice packages from multiplayer identity.
    public const string ModuleId = "game-voice-factions";
    public const string LegacyModuleId = "local-faction-voices";
    public static bool IsGenerated(string id) => id == ModuleId || id == LegacyModuleId;
    public static bool NeedsRuntime(UserSettings settings) => GameLanguages.Voice(settings) == "custom"
        && Groups.Take(5).Any(g => Language(settings, g) != Language(settings, "other"));
}
