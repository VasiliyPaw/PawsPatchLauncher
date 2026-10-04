using PawsPatchLauncher;
using System.Text.Json;

internal static class AiOptionsTests
{
    internal static void Run()
    {
        int count = 0;
        void Check(bool value, string why) { if (!value) throw new Exception(why); count++; }
        Check(new UserSettings().ImprovedAi, "New profiles enable AI improvements");
        Check(JsonSerializer.Deserialize("{}", LauncherJsonContext.Default.UserSettings)!.ImprovedAi, "Existing profiles default to enabled");
        var oldSuspended = JsonSerializer.Deserialize("{\"pawPatchEnabled\":false,\"suspendedArcaneComponents\":{}}", LauncherJsonContext.Default.UserSettings)!;
        GameMod.SetPawPatch(oldSuspended,true);
        Check(oldSuspended.ImprovedAi,"Old suspended settings use the new default when Paw's Patch is enabled");
        foreach (var language in UiLanguages.Choices)
        foreach (string key in new[] { "modules.ai", "modules.ai.desc", "modules.ai.help", "modules.siege.help", "modules.siege.beta.help" })
        {
            var value = new Localization(language.Code)[key];
            Check(!string.IsNullOrWhiteSpace(value) && value != key, "Missing localized text: " + language.Code + " " + key);
            if (language.Code != "en") Check(value != new Localization("en")[key], "English fallback: " + language.Code + " " + key);
        }
        foreach (var mod in new[] { GameMod.ArcaneWars, GameMod.Vanilla, GameMod.Immortals })
        foreach (var channel in new[] { "stable", "beta" })
        foreach (bool core in new[] { false, true })
        foreach (bool data in new[] { false, true })
        foreach (bool ai in new[] { false, true })
        {
            var s = new UserSettings { Mod=mod, Channel=channel, DataOnly=data, ImprovedAi=ai };
            GameMod.SetPawPatch(s, core);
            var active = EffectiveSettings.ForChannel(s);
            bool expected = mod == GameMod.ArcaneWars && core && !data && ai;
            Check(active.ImprovedAi == expected, "AI scope");
            var code = ConfigurationCode.Create(active);
            Check(ConfigurationCode.Parse(code).ImprovedAi == expected, "AI configuration roundtrip");
            Check(FriendConfiguration.TryParse(code, channel, out var incoming) && incoming.ImprovedAi == expected, "Friend transfer");
            var feed = new ChannelManifest { Channel=channel };
            Check(!EffectiveSettings.ForFeed(s,feed).ImprovedAi,"Old feed cannot enable new behavior");
            feed.Packages.Add(new PackageRelease { Id="ai-improvements", Mods=[GameMod.ArcaneWars] });
            Check(EffectiveSettings.ForFeed(s,feed).ImprovedAi==expected,"Available package scope");
            if (mod == GameMod.ArcaneWars)
                Check(FriendConfiguration.Components(s)["improved_ai"]==expected,"Presence AI flag follows effective settings");
        }
        var original = new UserSettings { Channel="beta" };
        GameMod.SetPawPatch(original,false); Check(!original.ImprovedAi,"Master disables AI");
        GameMod.SetPawPatch(original,true); Check(original.ImprovedAi,"Master restores preference");
        original.ImprovedAi=false; GameMod.SetPawPatch(original,false); GameMod.SetPawPatch(original,true);
        Check(!original.ImprovedAi,"Disabled preference remains disabled");
        const string old="PAW-BETA-IW1-SP4-RM1-SG1-LM1-RU0-CL1-OOS1";
        Check(!ConfigurationCode.Parse(old).ImprovedAi,"Old codes mean previous AI behavior");
        Check(ConfigurationCode.Parse(old.Replace("BETA","STABLE")+"-AI1").ImprovedAi,"Stable Arcane AI configuration accepted");
        foreach(var code in new[]{old+"-AI1-DATA",old+"-AI1-PP0",old.Replace("BETA","STABLE")+"-AI1-DATA",old.Replace("BETA","STABLE")+"-AI1-PP0","PAW-BETA-VANILLA-PP1-AI1",old+"-AI1-AI1"})
            Check(!FriendConfiguration.TryParse(code,code.Contains("STABLE")?"stable":"beta",out _),"Malformed AI code rejected");
        Console.WriteLine("AI_OPTIONS_PASS "+count);
    }
}
