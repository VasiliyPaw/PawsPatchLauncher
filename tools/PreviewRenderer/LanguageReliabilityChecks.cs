using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using PawsPatchLauncher;

namespace PreviewRenderer;
internal static class LanguageReliabilityChecks
{
    internal static void Run(string configPath, string language)
    {
        if (!ActivityStore.IsSmokeTest) throw new InvalidOperationException("Isolated profile required.");
        var config = JsonSerializer.Deserialize(File.ReadAllText(configPath), LauncherJsonContext.Default.LauncherConfiguration)!;
        var settings = JsonSerializer.Deserialize(File.ReadAllText(Path.Combine(Path.GetDirectoryName(configPath)!, "test-profile/settings.json")), LauncherJsonContext.Default.UserSettings)!;
        settings.Language = language; new SettingsStore().Save(settings);
        var client = new FeedClient(config);
        var modern = Task.Run(() => client.GetChannelAsync()).GetAwaiter().GetResult()!;
        Task.Run(async () =>
        {
            foreach (var package in ModLibrary.Packages(modern, settings.Mod))
                await client.DownloadVerifiedAsync(package, null);
            await new ModLibrary(settings.GamePath!).RememberAsync(modern, settings.Mod);
        }).GetAwaiter().GetResult();
        var legacy = JsonSerializer.Deserialize(JsonSerializer.Serialize(modern, LauncherJsonContext.Default.ChannelManifest), LauncherJsonContext.Default.ChannelManifest)!;
        legacy.Packages.RemoveAll(p => p.Id == "game-voice-ru");
        var w = new MainWindow(config, client); const BindingFlags flags = BindingFlags.Instance | BindingFlags.NonPublic;
        void Set(string name, object? value) => typeof(MainWindow).GetField(name, flags)!.SetValue(w, value);
        T Field<T>(string name) => (T)typeof(MainWindow).GetField(name, flags)!.GetValue(w)!;
        void Call(string name) => typeof(MainWindow).GetMethod(name, flags)!.Invoke(w, null);
        T C<T>(string name) => (T)w.FindName(name);
        var count = 0;
        void Check(bool ok, string why) { count++; if (!ok) throw new Exception("Language reliability: " + why); }
        try
        {
            Set("_game", new GameInstallation(settings.GamePath!, Path.Combine(settings.GamePath!, "k2.exe"), "fixture", "stable"));
            Set("_gameRunningProbe", new Func<bool>(() => false));
            Set("_compatibilityState", GameCompatibilityState.Supported);
            Set("_channel", modern); Set("_offeredModChannel", modern); Set("_latestChannel", modern);
            Call("RefreshStatus");
            Console.WriteLine($"initial pending={Field<bool>("_settingsPending")} installed={Field<bool>("_patchInstalled")} failure={Field<string?>("_installationFailure")} launch={C<Button>("LaunchButton").IsEnabled} tooltip={C<Button>("LaunchButton").ToolTip}");
            Check(!Field<bool>("_settingsPending") && C<Button>("LaunchButton").IsEnabled, "initial applied state blocked");
            var text = C<ComboBox>("GameLanguageCombo"); var voice = C<ComboBox>("GameVoiceCombo");
            Check(text.Items.Count == 4 && voice.Items.Count == 4, "missing language choices");
            for (var i = 1; i < 4; i++)
            {
                text.SelectedIndex = i;
                Check(GameLanguages.Text(Field<UserSettings>("_settings")) == GameLanguages.Choices[i], "wrong selected text");
                Check(Field<bool>("_settingsPending") && C<Button>("ApplySettingsButton").IsEnabled && !C<Button>("LaunchButton").IsEnabled, "text change lost Apply");
                text.SelectedIndex = 0;
                Check(!Field<bool>("_settingsPending") && C<Button>("ApplySettingsButton").Visibility == Visibility.Collapsed && C<Button>("LaunchButton").IsEnabled, "text return did not restore Launch");
                voice.SelectedIndex = i;
                Check(GameLanguages.Voice(Field<UserSettings>("_settings")) == GameLanguages.Choices[i], "wrong selected speech");
                Check(Field<bool>("_settingsPending") && C<Button>("ApplySettingsButton").IsEnabled && !C<Button>("LaunchButton").IsEnabled, "voice change lost Apply");
                voice.SelectedIndex = 0;
                Check(!Field<bool>("_settingsPending") && C<Button>("LaunchButton").IsEnabled, "voice return left pending state");
            }
            text.SelectedIndex = 2;
            text.SelectedIndex = 3;
            Check(GameLanguages.Text(Field<UserSettings>("_settings")) == "fr" && Field<bool>("_settingsPending"), "German to French lost Apply");
            text.SelectedIndex = 0;
            Field<UserSettings>("_settings").GameVoiceLanguage = "ru";
            Set("_offeredModChannel", legacy); Call("RefreshStatus"); Call("SyncLanguageChoices");
            Check(voice.IsEnabled, "older offered catalog hid supported speech from the retained release");
            Check(Field<bool>("_settingsPending") && !C<Button>("LaunchButton").IsEnabled && C<Button>("ApplySettingsButton").IsEnabled && Field<string?>("_installationFailure") is null,
                "older offered catalog blocked a supported retained configuration");
            Set("_offeredModChannel", modern); Call("RefreshStatus"); Call("SyncLanguageChoices");
            Check(voice.IsEnabled && C<Button>("ApplySettingsButton").IsEnabled && !C<Button>("LaunchButton").IsEnabled, "new catalog did not recover mixed languages");
            voice.SelectedIndex = 0;
            Check(!Field<bool>("_settingsPending") && C<Button>("LaunchButton").IsEnabled, "catalog recovery/reversion left stale error");
            Console.WriteLine($"LANGUAGE RELIABILITY PASS {count} {language}");
        }
        finally { w.Close(); }
    }
}
