// Local r4 only. The caller suspends only the newly launched, verified test game.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;

internal sealed class RandomSite
{
    internal uint Rva;
    internal byte[] Original, Replacement;
    internal int Entry = -1;
    internal byte Opcode;
    internal int[] Relocations = new int[0];
}

internal static class RandomMapPatch
{
    private static byte[] Resource(string name, string expected)
    {
        using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
        using (MemoryStream output = new MemoryStream())
        {
            if (stream == null) throw new InvalidDataException("Отсутствует ресурс случайной карты.");
            stream.CopyTo(output); byte[] data = output.ToArray();
            using (SHA256 sha = SHA256.Create())
                if (TerrainPatch.HexText(sha.ComputeHash(data)) != expected)
                    throw new InvalidDataException("Повреждён ресурс случайной карты.");
            return data;
        }
    }
    internal static byte[] Relocate(byte[] source, byte[] fixups, uint image, uint cave)
    {
        byte[] result = (byte[])source.Clone();
        if (fixups.Length % 12 != 0) throw new InvalidDataException("Неверная таблица адресов.");
        for (int i = 0; i < fixups.Length; i += 12)
        {
            int offset = BitConverter.ToInt32(fixups, i);
            if (offset < 0 || offset > result.Length - 4) throw new InvalidDataException("Адрес вне ресурса.");
            long value = BitConverter.ToUInt32(result, offset) +
                (long)BitConverter.ToInt32(fixups, i + 4) * ((long)image - 0x460000) +
                (long)BitConverter.ToInt32(fixups, i + 8) * ((long)cave - 0x30000000);
            Array.Copy(BitConverter.GetBytes(unchecked((uint)value)), 0, result, offset, 4);
        }
        return result;
    }
    private static byte[] Original(RandomSite site, uint image)
    {
        byte[] result = (byte[])site.Original.Clone();
        foreach (int offset in site.Relocations)
            Array.Copy(BitConverter.GetBytes(unchecked(BitConverter.ToUInt32(result, offset) + image - 0x460000)), 0, result, offset, 4);
        return result;
    }
    internal static byte[] Replacement(RandomSite site, uint image, uint cave)
    {
        if (site.Entry < 0) return site.Replacement;
        byte[] result = Enumerable.Repeat((byte)0x90, site.Original.Length).ToArray();
        result[0] = site.Opcode;
        Array.Copy(BitConverter.GetBytes(unchecked(cave + (uint)site.Entry - image - site.Rva - 5)), 0, result, 1, 4);
        return result;
    }
    internal static void Validate(IMemory mem, uint image)
    {
        foreach (RandomSite site in RandomMapBundle.Sites.Concat(RandomMapBundle.Guards))
            TerrainPatch.Expect(mem, image + site.Rva, Original(site, image));
    }
    internal static uint Install(IMemory mem, uint image, Action<string> log)
    {
        Validate(mem, image);
        byte[] payload = Resource("RandomMapPayload", RandomMapBundle.PayloadHash);
        byte[] fixups = Resource("RandomMapFixups", RandomMapBundle.FixupsHash);
        List<RandomSite> attempted = new List<RandomSite>(); uint cave = 0; bool safeToFree = true;
        try
        {
            cave = mem.Allocate(payload.Length);
            payload = Relocate(payload, fixups, image, cave);
            mem.Write(cave, payload); TerrainPatch.Expect(mem, cave, payload);
            mem.MakeExecutable(cave, payload.Length); mem.Flush(cave, payload.Length);
            foreach (RandomSite site in RandomMapBundle.Sites)
            {
                attempted.Add(site); safeToFree = false;
                byte[] bytes = Replacement(site, image, cave);
                mem.WriteCode(image + site.Rva, bytes);
                TerrainPatch.Expect(mem, image + site.Rva, bytes); mem.Flush(image + site.Rva, bytes.Length);
            }
            log("RANDOM_MAP_READY cave=0x" + cave.ToString("X8") + " profiles=5 originalProfilesUnchanged=true rngCallsAdded=0 commonSettings=true terrainDefaults=true");
            return cave;
        }
        catch
        {
            bool allRestored = true;
            foreach (RandomSite site in attempted.AsEnumerable().Reverse())
            {
                try
                {
                    byte[] before = Original(site, image);
                    mem.WriteCode(image + site.Rva, before); TerrainPatch.Expect(mem, image + site.Rva, before);
                    mem.Flush(image + site.Rva, before.Length);
                }
                catch (Exception e) { allRestored = false; log("RANDOM_ROLLBACK_UNCERTAIN " + e.Message); }
            }
            safeToFree = safeToFree || allRestored;
            if (cave != 0 && safeToFree) mem.Free(cave);
            throw;
        }
    }
    internal static void Verify(IMemory mem, uint image, uint cave)
    {
        foreach (RandomSite site in RandomMapBundle.Sites)
            TerrainPatch.Expect(mem, image + site.Rva, Replacement(site, image, cave));
        byte[] bytes = Relocate(Resource("RandomMapPayload", RandomMapBundle.PayloadHash),
            Resource("RandomMapFixups", RandomMapBundle.FixupsHash), image, cave);
        TerrainPatch.Expect(mem, cave, bytes);
    }
    internal static void GuardData(string root)
    {
        foreach (string[] input in RandomMapBundle.Inputs)
        {
            string path = Path.Combine(root, "data", input[0]);
            if (!File.Exists(path) || ReleaseStartup.Hash(path) != input[1])
                throw new InvalidDataException("Случайная карта: отличается необходимый файл. Игра не запущена: " + path);
        }
    }
    internal static int SelfTest()
    {
        int count = 0; Action<string> quiet = delegate { };
        Action<bool> check = delegate(bool ok) { count++; if (!ok) throw new Exception("Random map transaction test failed."); };
        foreach (uint image in new uint[] { 0x460000, 0x640000, 0xaf0000 })
        {
            Func<FakeMemory> seed = delegate
            {
                FakeMemory m = new FakeMemory(image);
                foreach (RandomSite s in RandomMapBundle.Sites.Concat(RandomMapBundle.Guards)) m.Seed(image + s.Rva, Original(s,image));
                return m;
            };
            FakeMemory ok = seed(); uint cave = Install(ok,image,quiet); int operations = ok.Operations;
            Verify(ok,image,cave); check(ok.Allocated);
            for (int at = 1; at <= operations; at++)
            {
                FakeMemory f = seed(); f.FailAt = at; bool thrown = false;
                try { Install(f,image,quiet); } catch (IOException) { thrown = true; }
                f.FailAt = -1; check(thrown && !f.Allocated);
                foreach (RandomSite s in RandomMapBundle.Sites) check(f.Read(image+s.Rva,s.Original.Length).SequenceEqual(Original(s,image)));
            }
            foreach (RandomSite s in RandomMapBundle.Sites.Concat(RandomMapBundle.Guards))
            {
                FakeMemory bad = seed(); bad.Seed(image+s.Rva,new byte[s.Original.Length]); bool thrown = false;
                try { Install(bad,image,quiet); } catch (InvalidOperationException) { thrown = true; }
                check(thrown && !bad.Allocated);
            }
            FakeMemory partial = seed(); partial.AlwaysFailHook = true;
            try { Install(partial,image,quiet); } catch (IOException) { }
            check(partial.Allocated && partial.Frees==0);
        }
        return count;
    }
}
