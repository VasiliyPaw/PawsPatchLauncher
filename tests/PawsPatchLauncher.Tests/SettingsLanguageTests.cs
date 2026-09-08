using System.Globalization;
using System.Text.Json;
using PawsPatchLauncher;

internal static class SettingsLanguageTests
{
    public static int Run(string root)
    {
        var count=0;
        void Check(bool ok,string reason){count++;if(!ok)throw new Exception("Settings language: "+reason);}
        var previous=CultureInfo.CurrentUICulture;
        try
        {
            Check(new UserSettings().Language=="en","model default is not English");
            foreach(var culture in new[]{"ru-RU","en-US","cs-CZ"})
            {
                CultureInfo.CurrentUICulture=CultureInfo.GetCultureInfo(culture);
                var directory=Path.Combine(root,"language",culture);
                var store=new SettingsStore(directory);
                var settings=store.Load();
                Check(settings.Language=="en","first launch followed OS culture: "+culture);
                Check(!Directory.Exists(directory),"reading defaults wrote user preferences");
                Check(settings.RussianLocalization&&settings.Channel=="stable"&&settings.RoamingSpawnMode=="x4","interface language changed gameplay defaults");
                settings.Language="ru";settings.GamePath="Fixture game path";settings.NotificationVolume=37;
                store.Save(settings);
                var restored=new SettingsStore(directory).Load();
                Check(restored.Language=="ru","explicit Russian choice lost on restart");
                Check(restored.GamePath==settings.GamePath&&restored.NotificationVolume==37,"unrelated saved preferences changed");
                restored.Language="en";store.Save(restored);
                Check(new SettingsStore(directory).Load().Language=="en","explicit English choice lost on restart");
                File.WriteAllText(Path.Combine(directory,"settings.json"),"{}");
                Check(store.Load().Language=="en","missing language does not use English");
                File.WriteAllText(Path.Combine(directory,"settings.json"),"null");
                Check(store.Load().Language=="en","null settings fallback depends on culture");
                File.WriteAllText(Path.Combine(directory,"settings.json"),"{invalid");
                Check(store.Load().Language=="en","damaged settings fallback depends on culture");
            }
            var legacy=JsonSerializer.Deserialize("{\"language\":\"ru\"}",LauncherJsonContext.Default.UserSettings)!;
            Check(legacy.Language=="ru","existing Russian profile was migrated to English");
        }
        finally{CultureInfo.CurrentUICulture=previous;}
        Console.WriteLine($"SETTINGS LANGUAGE PASS {count}: English first launch across OS cultures, saved RU/EN, isolated persistence and fallbacks");
        return count;
    }
}
