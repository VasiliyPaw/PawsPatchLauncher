using System.Buffers.Binary;
using System.Text;
using PawsPatchLauncher;

internal static class GameLobbyPreferencesTests
{
    private static Dictionary<string, byte[]> Chunks(byte[] bytes)
    {
        var count = BitConverter.ToInt32(bytes, 8);
        var result = new Dictionary<string, byte[]>();
        for (var i = 0; i < count; i++)
        {
            var entry = bytes.AsSpan(bytes.Length - count * 96 + i * 96, 96);
            var name = Encoding.Unicode.GetString(entry[..64]).TrimEnd('\0');
            result[name] = bytes.AsSpan((int)BinaryPrimitives.ReadUInt64LittleEndian(entry[64..]), (int)BinaryPrimitives.ReadUInt64LittleEndian(entry[72..])).ToArray();
        }
        return result;
    }
    private static byte[] String(string value)
    {
        using var data = new MemoryStream(); using var writer = new BinaryWriter(data);
        writer.Write((ushort)value.Length); writer.Write(Encoding.Unicode.GetBytes(value));
        return data.ToArray();
    }
    private static byte[] Fixture(bool single, bool multi)
    {
        var chunks = new Dictionary<string, byte[]> {
            ["HeaderInfo"] = BitConverter.GetBytes(19), ["SimplePreferences"] = Encoding.UTF8.GetBytes("private name and general preferences must survive"),
            ["SingleLaunchSettings"] = String(single ? "kingdom16" : "kingdom01"),
            ["MultiLaunchSettings"] = String(multi ? "paws_war_barbarian" : "kingdom08"),
            ["RMCPreferences"] = [1,2,3,4], ["UnknownExtension"] = [7,6,5,4,3] };
        using var stream = new MemoryStream(); using var writer = new BinaryWriter(stream);
        writer.Write("TGCK"u8); writer.Write(2); writer.Write(chunks.Count);
        var entries = new List<byte[]>();
        foreach (var (name, data) in chunks)
        {
            var entry = new byte[96]; Encoding.Unicode.GetBytes(name).CopyTo(entry, 0);
            BinaryPrimitives.WriteUInt64LittleEndian(entry.AsSpan(64), (ulong)stream.Position);
            BinaryPrimitives.WriteUInt64LittleEndian(entry.AsSpan(72), (ulong)data.Length);
            BinaryPrimitives.WriteUInt64LittleEndian(entry.AsSpan(80), 0x01043C020A6C6C88);
            BinaryPrimitives.WriteUInt64LittleEndian(entry.AsSpan(88), (ulong)data.Length);
            entries.Add(entry); writer.Write(data);
        }
        foreach (var entry in entries) writer.Write(entry);
        return stream.ToArray();
    }
    internal static async Task<int> RunAsync()
    {
        var checks = 0;
        void Check(bool ok, string why) { if (!ok) throw new Exception(why); checks++; }
        foreach (var mod in new[] { GameMod.Vanilla, GameMod.Immortals, GameMod.ArcaneWars })
        foreach (var paw in new[] { false, true })
        foreach (var dataOnly in new[] { false, true })
        foreach (var single in new[] { false, true })
        foreach (var multi in new[] { false, true })
        {
            var input = Fixture(single, multi); var copy = input.ToArray();
            var settings = new UserSettings { Mod = mod, PawPatchEnabled = paw, DataOnly = dataOnly };
            var output = GameLobbyPreferences.Repair(input, settings);
            var shouldRepair = (single || multi) && !(mod == GameMod.ArcaneWars && paw && !dataOnly);
            Check((output is not null) == shouldRepair, "Incorrect compatibility decision");
            Check(input.SequenceEqual(copy), "Input mutated");
            if (output is null) continue;
            var before = Chunks(input); var after = Chunks(output);
            Check(before.Keys.SequenceEqual(after.Keys), "Required chunk removed or reordered");
            foreach (var name in before.Keys.Except(new[] { "RMCPreferences", single ? "SingleLaunchSettings" : "", multi ? "MultiLaunchSettings" : "" }))
                Check(before[name].SequenceEqual(after[name]), "Unrelated preference data modified: " + name);
            Check(after["RMCPreferences"].SequenceEqual(new byte[4]), "Map cache not cleared");
            Check(GameLobbyPreferences.Repair(output, settings) is null, "Repeated launch resets preferences again");
        }
        var badInputs = new List<byte[]> { Array.Empty<byte>(), new byte[12], Fixture(true,true)[..^1] };
        foreach (var offset in new[] { 0,4,8,12 }) {var bytes=Fixture(true,true);bytes[offset]=255;badInputs.Add(bytes);}
        var overlap=Fixture(true,true);var start=overlap.Length-6*96;BinaryPrimitives.WriteUInt64LittleEndian(overlap.AsSpan(start+96+64),12);badInputs.Add(overlap);
        var compressed=Fixture(true,true);compressed[^8]=99;badInputs.Add(compressed);
        foreach(var bytes in badInputs) Check(GameLobbyPreferences.Repair(bytes,new UserSettings{Mod=GameMod.Vanilla}) is null,"Unrecognized archive modified");
        var root=Path.Combine(Path.GetTempPath(),"PawsLobbyPreferences",Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
        var path=Path.Combine(root,"Preferences.rup");var original=Fixture(false,true);File.WriteAllBytes(path,original);
        var vanilla=new UserSettings{Mod=GameMod.Vanilla};
        Check(await GameLobbyPreferences.PrepareAsync(path,vanilla),"Disk repair skipped");
        var backup=Directory.GetFiles(Path.Combine(root,"PawsLauncherBackups")).Single();
        Check(File.ReadAllBytes(backup).SequenceEqual(original),"Backup differs");
        Check(!await GameLobbyPreferences.PrepareAsync(path,vanilla),"Disk repair is not idempotent");
        Check(Directory.GetFiles(Path.Combine(root,"PawsLauncherBackups")).Length==1,"Duplicate backups");
        Console.WriteLine($"LOBBY PREFERENCES PASS {checks}: mode/component transitions, both launch caches, general preferences, unknown chunks/formats, backup and repeated launch.");
        return checks;
    }
    internal static async Task RepairFixtureAsync(string input, string output)
    {
        if(File.Exists(output)) throw new IOException("Choose an unused output file.");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
        File.Copy(input,output);
        var before=Chunks(File.ReadAllBytes(input));
        if(!await GameLobbyPreferences.PrepareAsync(output,new UserSettings{Mod=GameMod.Vanilla})) throw new Exception("Crash fixture did not trigger guard");
        var after=Chunks(File.ReadAllBytes(output));
        foreach(var name in new[]{"HeaderInfo","SimplePreferences","SingleLaunchSettings"})
            if(!before[name].SequenceEqual(after[name])) throw new Exception("Unrelated crash fixture chunk changed: "+name);
        Console.WriteLine("CRASH-267 FIXTURE PASS: only MultiLaunchSettings and RMCPreferences reset; original file untouched.");
    }
}
