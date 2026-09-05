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
                return JsonSerializer.Deserialize(File.ReadAllText(SettingsPath), LauncherJsonContext.Default.UserSettings) ?? new UserSettings();
        }
        catch { }

        return new UserSettings { Language = System.Globalization.CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "ru" ? "ru" : "en" };
    }

    public void Save(UserSettings settings)
    {
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
            return JsonSerializer.Deserialize(embedded, LauncherJsonContext.Default.LauncherConfiguration) ?? throw new InvalidDataException("Launcher configuration is invalid.");
        }
        return JsonSerializer.Deserialize(File.ReadAllText(path), LauncherJsonContext.Default.LauncherConfiguration)
               ?? new LauncherConfiguration();
    }
}
