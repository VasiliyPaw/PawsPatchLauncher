using System.Text.Json;

namespace PawsPatchLauncher;

public sealed class SettingsStore
{
    private readonly string _directory = ActivityStore.Root;
    private string SettingsPath => Path.Combine(_directory, "settings.json");

    public UserSettings Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                var saved = JsonSerializer.Deserialize(File.ReadAllText(SettingsPath), LauncherJsonContext.Default.UserSettings);
                if (saved is not null)
                {
                    if (!saved.PawPatchEnabled) GameMod.DisableArcaneComponents(saved);
                    ModChannelSelection.Remember(saved); return saved;
                }
            }
        }
        catch { }

        // Fresh installs start with the original game; legacy profiles keep their Arcane Wars defaults.
        return new UserSettings { Mod = GameMod.Vanilla, Language = System.Globalization.CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "ru" ? "ru" : "en" };
    }

    public void Save(UserSettings settings)
    {
        if (!settings.PawPatchEnabled) GameMod.DisableArcaneComponents(settings);
        ModChannelSelection.Remember(settings);
        Directory.CreateDirectory(_directory);
        var temporary = SettingsPath + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(settings, LauncherJsonContext.Default.UserSettings));
        File.Move(temporary, SettingsPath, true);
    }

    public static LauncherConfiguration LoadConfiguration()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "launcher.config.json");
        if (!File.Exists(path))
        {
            using var embedded = typeof(SettingsStore).Assembly.GetManifestResourceStream("PawsPatchLauncher.launcher.config.json")
                ?? throw new InvalidDataException("Launcher configuration is missing.");
            return OfficialFeedConfiguration.Upgrade(JsonSerializer.Deserialize(embedded, LauncherJsonContext.Default.LauncherConfiguration) ?? throw new InvalidDataException("Launcher configuration is invalid."));
        }
        return OfficialFeedConfiguration.Upgrade(JsonSerializer.Deserialize(File.ReadAllText(path), LauncherJsonContext.Default.LauncherConfiguration)
               ?? new LauncherConfiguration());
    }
}
