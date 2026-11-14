using System.Text;
using System.Text.RegularExpressions;
using PawsPatchLauncher;
using PawsPatchLauncher.Rwd;

internal static class FactionVoiceCommentTests
{
    internal static async Task<int> RunAsync(string root)
    {
        var count = 0;
        void Check(bool ok, string why) { count++; if (!ok) throw new Exception("Faction voice comment: " + why); }
        var game = Path.Combine(root, "faction-inline-comment"); Directory.CreateDirectory(game);
        const string first = "sounds/FemaleHeroes/HarounCoFemaleMove01.wav";
        const string second = "sounds/FemaleHeroes/HarounCoFemaleMove02.wav";
        const string third = "sounds/FemaleHeroes/HarounCoFemaleMove03.wav";
        // Actual stock cue syntax: two recordings, then a disabled third.
        var table = "[Audio Template=HeroCallout]\n{\n IDS = haroun_co_f_move\n files = " + first + ", " + second + ", ;" + third + "\n}\n"
            + "[Audio Template=HeroCallout]\n{\n IDS = unchanged_select\n files = " + first + ", " + second + "\n}\n"
            + "[Audio Template=HeroCallout]\n{\n IDS = comment_no_comma\n files = \"" + first + "\"; disabled recording\n}\n"
            + "[Audio Template=HeroCallout]\n{\n IDS = unavailable_mod_cue\n files = " + first + ", " + third + "\n}\n";
        var bytes = Encoding.Unicode.GetPreamble().Concat(Encoding.Unicode.GetBytes(table)).ToArray();
        RwdArchive.Write(Path.Combine(game, "Data.rwd"), new Dictionary<string, byte[]>
        { ["Audio/speech.tgi"] = bytes, ["Audio/" + first] = [1], ["Audio/" + second] = [2] });
        var desired = new Dictionary<string, InstalledModule>();
        foreach (var language in new[] { "ru", "de", "fr" })
        {
            var module = new InstalledModule { Enabled = true, Version = "test", ArchiveSha256 = language, Priority = 100 };
            foreach (var path in new[] { first, second })
            {
                var relative = "data/Audio/" + path;
                var target = Path.Combine(game, ".pawpatch/packages/game-voice-" + language, "test/payload", relative);
                Directory.CreateDirectory(Path.GetDirectoryName(target)!); await File.WriteAllBytesAsync(target, [3]);
                module.Files.Add(new ModuleFile { Path = relative, Size = 1 });
            }
            desired["game-voice-" + language] = module;
        }
        var settings = new UserSettings { GameVoiceLanguage = "custom" };
        CustomVoices.Initialize(settings, "ru"); settings.FactionVoiceLanguages["council"] = "en";
        var result = await FactionVoiceResources.ComposeAsync(game, desired, settings, default);
        var generated = result[CustomVoices.ModuleId];
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.ArcaneWars, GameMod.Immortals })
        {
            settings.Mod = mod;
            var state = new InstallState { AppliedSettings = settings };
            state.Modules[CustomVoices.ModuleId] = new InstalledModule { Enabled = true, Version = new string('A', 64) };
            Check(UpdateDetector.HasSettingsChanges(state, [], settings), "old generated cache did not request Apply settings for " + mod);
            state.Modules[CustomVoices.ModuleId] = generated;
            Check(!UpdateDetector.HasSettingsChanges(state, [], settings), "current generated cache keeps requesting Apply settings for " + mod);
            state.Modules[CustomVoices.ModuleId].Enabled = false;
            Check(UpdateDetector.HasSettingsChanges(state, [], settings), "disabled generated cache was accepted for " + mod);
            generated.Enabled = true;
            state.Modules.Clear();
            Check(UpdateDetector.HasSettingsChanges(state, [], settings), "missing generated cache was accepted for " + mod);
            settings.GameVoiceLanguage = "en";
            Check(!UpdateDetector.HasSettingsChanges(state, [], settings), "ordinary speech needs faction cache for " + mod);
            settings.GameVoiceLanguage = "custom";
        }
        var pathToTable = Path.Combine(game, ".pawpatch/packages", CustomVoices.ModuleId, generated.Version, "payload/data/Audio/paws_faction_voices.tgi");
        var generatedText = await File.ReadAllTextAsync(pathToTable);
        foreach (var language in GameLanguages.VoiceChoices)
        {
            Check(generatedText.Contains("IDS = paws_voice_" + language + "_haroun_co_f_move"), "move cue missing for " + language);
            Check(generatedText.Contains("PawVoices/" + language + "/" + first), "first recording missing for " + language);
            Check(generatedText.Contains("PawVoices/" + language + "/" + second), "second recording missing for " + language);
            Check(generatedText.Contains("IDS = paws_voice_" + language + "_unchanged_select"), "ordinary cue lost for " + language);
            Check(generatedText.Contains("IDS = paws_voice_" + language + "_comment_no_comma"), "quoted/comment cue lost for " + language);
        }
        Check(!generatedText.Contains(third) && !generatedText.Contains(';'), "disabled recording leaked into generated file list");
        Check(!generatedText.Contains("unavailable_mod_cue"), "genuinely unavailable mod recording was fabricated");
        foreach (Match line in Regex.Matches(generatedText, @"(?im)^\s*files\s*=\s*([^\r\n]+)"))
        foreach (var reference in line.Groups[1].Value.Split(','))
            Check(File.Exists(Path.Combine(Path.GetDirectoryName(pathToTable)!, reference.Trim())), "generated cue references missing audio");
        var reused = await FactionVoiceResources.ComposeAsync(game, desired, settings, default);
        Check(reused[CustomVoices.ModuleId].Version == generated.Version, "valid regenerated resources were not reusable");
        return count;
    }
}
