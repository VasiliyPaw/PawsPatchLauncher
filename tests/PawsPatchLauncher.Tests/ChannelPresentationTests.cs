using PawsPatchLauncher;

internal static class ChannelPresentationTests
{
    internal static int Run()
    {
        int checks = 0;
        void Equal(string expected, string actual) { if (actual != expected) throw new Exception($"Channel display: expected {expected}, got {actual}"); checks++; }
        Equal("Релиз", ChannelPresentation.Name("stable", "ru"));
        Equal("Release", ChannelPresentation.Name("STABLE", "en"));
        Equal("Бета", ChannelPresentation.Name("beta", "ru"));
        Equal("Beta", ChannelPresentation.Name("BETA", "en"));
        Equal("custom", ChannelPresentation.Name("custom", "ru"));
        Equal("Каналы Релиз и Beta", ChannelPresentation.ChangelogText("Каналы Stable и Beta", "ru"));
        Equal("Release/Beta channels", ChannelPresentation.ChangelogText("Stable/Beta channels", "en"));
        Equal("Релиз, Релиз, Релиз.", ChannelPresentation.ChangelogText("stable, STABLE, стейбл.", "ru"));
        Equal("Релиз - проверенная версия", ChannelPresentation.ChangelogText("Stable \u2014 проверенная версия", "ru"));
        Equal("Release - tested version", ChannelPresentation.ChangelogText("Stable \u2013 tested version", "en"));
        Equal("", ChannelPresentation.PlainPunctuation(""));
        Equal("before-after; 1-4; title - details", ChannelPresentation.PlainPunctuation("before\u2014after; 1\u20134; title \u2015 details"));
        Equal("Первая строка - текст\nВторая - текст.", ChannelPresentation.PlainPunctuation("Первая строка \u2014 текст\nВторая \u2013 текст."));
        Equal("SHA-256 / beta.6 / PAW-STABLE-IW1", ChannelPresentation.PlainPunctuation("SHA-256 / beta.6 / PAW-STABLE-IW1"));
        foreach (var literal in new[] { "https://example.test/build\u2014one", "`a\u2014b`", "C:\\Games\\Kohan\u2014II\\k2.exe",
                     "\"C:\\Мои игры\u2014тест\\k2.exe\"", "«C:\\Games\u2014test\\k2.exe»", "\\\\server\\share\u2013beta\\patch.zip",
                     "data/colors\u2014test.ini", "patch\u2014beta.zip" })
            Equal(literal + " - описание", ChannelPresentation.PlainPunctuation(literal + " \u2014 описание"));
        var plain = ChannelPresentation.PlainPunctuation("Обновления \u2014 важные; версии 1\u20134");
        Equal(plain, ChannelPresentation.PlainPunctuation(plain));
        var strings = (Dictionary<string, (string Ru, string En)>)typeof(Localization)
            .GetField("Strings", System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.NonPublic)!.GetValue(null)!;
        Equal("", string.Join(",", strings.Where(pair => pair.Value.Ru.Any(c => c is >= '\u2013' and <= '\u2015')).Select(pair => pair.Key)));
        Equal("", string.Join(",", strings.Where(pair => pair.Value.En.Any(c => c is >= '\u2013' and <= '\u2015')).Select(pair => pair.Key)));
        foreach (var preserved in new[] { "PAW-STABLE-IW1-SP4-RM1-SG1-LM1-RU1-CL0-OOS0", "feed/stable.json", @"C:\stable\launcher.exe", "https://example.test/?channel=stable", "`stable`", "unstable", "stable_build" })
            Equal(preserved, ChannelPresentation.ChangelogText(preserved, "ru"));
        var settings = new UserSettings { Channel = "stable", CustomPlayerColors = false };
        var code = ConfigurationCode.Create(settings);
        Equal("PAW-STABLE", string.Join('-', code.Split('-').Take(2)));
        Equal("stable", ConfigurationCode.Parse(code).Channel);
        var channel = new ChannelManifest { Channel = "stable", Changelog = [new() { Title = new() { Ru = "Stable" } }] };
        var fingerprint = ChannelFingerprint.Create(channel);
        _ = ChannelPresentation.ChangelogText(channel.Changelog[0].Title.Ru, "ru");
        Equal("Stable", channel.Changelog[0].Title.Ru);
        Equal(fingerprint, ChannelFingerprint.Create(channel));
        channel.Changelog[0].Body.Ru = "Цвета \u2014 исправления";
        var originalBytes = System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(channel);
        Equal("Цвета - исправления", ChannelPresentation.ChangelogText(channel.Changelog[0].Body.Ru, "ru"));
        Equal(Convert.ToHexString(originalBytes), Convert.ToHexString(System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(channel)));
        Console.WriteLine($"CHANNEL PRESENTATION PASS {checks}: RU/EN names and punctuation, literal URLs/paths/codes, stored IDs, signed-model bytes and fingerprint isolation");
        return checks;
    }
}
