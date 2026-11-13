using PawsPatchLauncher;

internal static class MissingExecutableTests
{
    internal static int Run(string root)
    {
        var checks = 0;
        void Check(bool value, string why) { if (!value) throw new Exception("Missing executable: " + why); checks++; }
        var game = Path.Combine(root, "missing-executable-fixture"); Directory.CreateDirectory(game);
        Check(MissingGameExecutable.Find(null) is null, "empty path has antivirus warning");
        Check(MissingGameExecutable.Find(Path.Combine(game, "absent")) is null, "absent folder is called a missing EXE");
        Check(MissingGameExecutable.Find(game) is null, "arbitrary folder is called an installation");
        File.WriteAllText(Path.Combine(game, "Data.rwd"), "isolated detector fixture, no game data");
        var missing = MissingGameExecutable.Find(game);
        Check(GameLocator.FindMissingExecutable([Path.Combine(game, "absent"), game])?.Path == missing?.Path, "first-run Steam candidates miss recognizable installation");
        Check(missing is { IsPatchHelper: false, FileName: "k2.exe" }, "base EXE loss was not detected");
        Check(missing!.Directory == Path.GetFullPath(game), "recovery path was lost");
        Check(MissingGameExecutable.Find('"' + game + '"')?.Path == missing.Path, "quoted folder was not normalized");
        File.WriteAllText(Path.Combine(game, "k2.exe"), "fixture only; never executed");
        Check(MissingGameExecutable.Find(game) is null, "restored base file is still missing");
        const string helper = "k2_paws_pure_fixes_1372.exe";
        Check(MissingGameExecutable.Find(game, helper) is null, "uninstalled helper is called quarantined");
        var module = new InstalledModule { Enabled = true, Files = [new ModuleFile { Path = helper }] };
        var state = new InstallState(); state.Modules["pure-fixes-runtime"] = module;
        Check(MissingGameExecutable.Find(game, helper, state)?.IsPatchHelper == true, "managed helper loss was ignored");
        module.Enabled = false;
        Check(MissingGameExecutable.Find(game, helper, state) is null, "disabled component causes warning");
        module.Enabled = true; module.Files[0].Path = "subfolder/" + helper;
        Check(MissingGameExecutable.Find(game, helper, state) is null, "different manifest path causes warning");
        module.Files[0].Path = helper.ToUpperInvariant();
        Check(MissingGameExecutable.Find(game, helper, state)?.FileName == helper, "manifest casing changes detection");
        Check(MissingGameExecutable.Find(game, "other.exe", state) is null, "unselected component causes warning");
        Check(MissingGameExecutable.Find(game, "file.dll", state) is null, "non-executable causes warning");
        File.WriteAllText(Path.Combine(game, helper), "fixture only; never executed");
        Check(MissingGameExecutable.Find(game, helper, state) is null, "restored helper is still missing");
        File.Delete(Path.Combine(game, "k2.exe"));
        Check(MissingGameExecutable.Find(game, helper, state)?.IsPatchHelper == false, "helper hides missing base EXE");
        File.Delete(Path.Combine(game, "Data.rwd")); Directory.CreateDirectory(Path.Combine(game, ".pawpatch"));
        File.WriteAllText(Path.Combine(game, ".pawpatch/state.json"), "{}");
        Check(MissingGameExecutable.Find(game)?.FileName == "k2.exe", "retained installation state is not recognized");
        Check(MissingGameExecutable.Find("\0invalid") is null, "invalid path crashes detection");
        Console.WriteLine($"MISSING EXECUTABLE PASS {checks}: recognizable folder, base/helper loss, manifest ownership, restoration, wrong/moved folders and retained path");
        return checks;
    }
}
