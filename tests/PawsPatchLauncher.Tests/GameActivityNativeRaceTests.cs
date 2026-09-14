using System.Text;
using PawsPatchLauncher;

internal static class GameActivityNativeRaceTests
{
    public static int Run()
    {
        var checks = 0;
        void Check(bool ok, string label) { if (!ok) throw new Exception("Native activity identity/race: " + label); checks++; }
        foreach (var image in new uint[] { 0x400000, 0x460000, 0x750000 })
        {
            var memory = new Memory(image);
            GameActivity? Snapshot() => KohanActivityReader.ReadSnapshot(image, memory.Read);
            memory.Player(0, false); memory.Player(1, true);
            memory.U32(Memory.Manager + 0xc, memory.PlayerAddress(0));
            Check(Snapshot() is { Self: "p1", Players.Count: 2 }, "manager local pointer is player wrapper, not network peer");
            memory.U32(memory.PlayerAddress(0) + 4, 0);
            Check(Snapshot()?.Self == "p1", "local identity survives missing network peer");
            memory.U32(Memory.Manager + 0xc, memory.PlayerAddress(1));
            Check(Snapshot()?.Self is null, "bot cannot be publisher");
            memory.U32(Memory.Manager + 0xc, 0x2400000);
            memory.U32(memory.PlayerAddress(0) + 4, 0x2400000);
            Check(Snapshot()?.Self is null, "network-peer equality cannot impersonate local wrapper");
            memory.U32(Memory.Manager + 0xc, 0);
            Check(Snapshot()?.Self is null, "one human among bots is not enough evidence for identity");
            memory.U32(Memory.Manager + 0xc, memory.PlayerAddress(0));
            for (var i = 2; i < 12; i++) memory.Player(i, true);
            Check(Snapshot() is { Self: "p1", Players.Count: 12 }, "reported twelve-player solo-with-bots roster keeps publisher");

            Check(Snapshot()?.Players?[0] is { Race: "human", Subrace: "royalist" }, "lobby reads definition IDs");
            foreach (var race in new[] { "human", "drauga", "gauri", "haroun", "shadow", "undead" })
            {
                memory.Id(Memory.Nation, race);
                Check(Snapshot()?.Players?[0].Race == race, "race " + race);
            }
            foreach (var faction in new[] { "ceyah", "council", "fallen", "nationalist", "royalist" })
            {
                memory.Id(Memory.Faction, faction);
                Check(Snapshot()?.Players?[0].Subrace == faction, "faction " + faction);
            }
            memory.Id(Memory.Nation, "Mod_Race-2");
            Check(Snapshot()?.Players?[0].Race == "mod_race-2", "mod IDs normalized without hardcoded whitelist");
            foreach (var malformed in new[] { "", "haroun\n", "#localized_name", new string('a', 81) })
            {
                memory.Id(Memory.Nation, malformed);
                Check(Snapshot() is { Players.Count: 12 } snap && snap.Players[0].Race is null, "invalid ID omitted, not truncated or mislabeled");
            }
            memory.Id(Memory.Nation, "human");
            memory.U32(Memory.Entry + 0x18, 0);
            Check(Snapshot()?.Players?[0] is { Race: "random", Subrace: "royalist" }, "random race preserves selected faction");
            memory.U32(Memory.Entry + 0x18, Memory.Nation); memory.U32(Memory.Entry + 0x1c, 0);
            Check(Snapshot()?.Players?[0] is { Race: "human", Subrace: "random" }, "random faction preserves selected race");
            memory.U32(Memory.Entry + 0x18, 0);
            Check(Snapshot()?.Players?[0] is { Race: "random", Subrace: "random" }, "both lobby choices random");
            for (uint kind = 0; kind <= 5; kind++)
            {
                memory.U32(Memory.Session + 0x64, kind);
                Check(Snapshot()?.Players?[0] is { Race: "random", Subrace: "random" }, "same native WorldCreator selection including saves " + kind);
            }
            memory.U32(Memory.Entry + 0x18, 5);
            Check(Snapshot()?.Players?[0].Race is null, "invalid nonnull pointer is not Random");
            memory.U32(Memory.Entry + 0x18, 0);
            var lobbyReads = 0;
            byte[] LobbyTransition(uint address, int size) => address == Memory.Entry + 0x18 && ++lobbyReads == 2 ? BitConverter.GetBytes(Memory.Nation) : memory.Read(address, size);
            Check(KohanActivityReader.ReadSnapshot(image, LobbyTransition) is null, "lobby choice transition cannot mix snapshots");

            memory.Match();
            Check(Snapshot()?.Players?[0] is { Race: "haroun", Subrace: "council" }, "match uses assigned race and faction instance definition, not random template");
            memory.U32(Memory.Kingdom + 0x240, 0); memory.U32(Memory.Kingdom + 0x23c, 0);
            Check(Snapshot()?.Players?[0] is { Race: null, Subrace: null }, "missing actual match descriptors remain unknown");
            memory.Match();
            var changes = 0;
            byte[] RaceTransition(uint address, int size) => address == Memory.Kingdom + 0x240 && ++changes == 2 ? BitConverter.GetBytes(0u) : memory.Read(address, size);
            Check(KohanActivityReader.ReadSnapshot(image, RaceTransition) is null, "race transition cannot mix snapshots");
            changes = 0;
            byte[] FactionDefinitionTransition(uint address, int size) => address == 0x2051004 && ++changes == 2 ? BitConverter.GetBytes(Memory.Faction) : memory.Read(address, size);
            Check(KohanActivityReader.ReadSnapshot(image, FactionDefinitionTransition) is null, "faction definition transition cannot mix snapshots");
            changes = 0;
            byte[] IdentityTransition(uint address, int size) => address == Memory.Manager + 0xc && ++changes == 2 ? BitConverter.GetBytes(0u) : memory.Read(address, size);
            Check(KohanActivityReader.ReadSnapshot(image, IdentityTransition) is null, "owner transition cannot publish wrong identity");
            changes = 0;
            byte[] ManagerTransition(uint address, int size) => address == image + 0x5f3fec && ++changes == 2 ? BitConverter.GetBytes(0u) : memory.Read(address, size);
            Check(KohanActivityReader.ReadSnapshot(image, ManagerTransition) is null, "manager transition cannot publish wrong identity");
        }
        Console.WriteLine($"NATIVE GAME ACTIVITY IDENTITY/RACE PASS {checks}");
        return checks;
    }

    private sealed class Memory
    {
        public const uint Session = 0x2000000, Manager = 0x2010000, Creator = 0x2020000, Entry = 0x2030000;
        public const uint Nation = 0x2040000, Faction = 0x2041000, Kingdom = 0x2050000;
        private readonly uint image;
        private readonly Dictionary<uint, byte> data = new();
        public Memory(uint image)
        {
            this.image = image;
            Bytes(image + 0x1618a5, [0x8b, 0x41, 0x04, 0x83, 0xe8, 0x00]); Bytes(image + 0x15d1e7, [0x8b, 0x41, 0x04, 0xc3]);
            U32(image + 0x5f3fe4, Session); U32(image + 0x5f3fec, Manager); U32(Session + 0xf0, 1);
            foreach (var offset in new uint[] { 0x78, 0x7c, 0x80, 0x88 }) U32(Session + offset, Creator);
            Bytes(Creator + 0x3c, BitConverter.GetBytes(192f)); Bytes(Creator + 0x40, BitConverter.GetBytes(256f));
            U32(Creator + 0x14, Entry); U32(Creator + 0x18, 1);
            U32(Entry, 0x2031000); Text(0x2031000, "kingdom0");
            U32(Entry + 0x18, Nation); U32(Entry + 0x1c, Faction); Id(Nation, "human"); Id(Faction, "royalist");
        }
        public uint PlayerAddress(int index) => 0x2100000 + (uint)index * 0x100;
        public void Player(int index, bool bot)
        {
            var player = PlayerAddress(index); var node = 0x2110000 + (uint)index * 8; var name = 0x2120000 + (uint)index * 0x100;
            U32(node, player); if (index == 0) U32(Session + 0xc8, node); else U32(node - 4, node);
            U32(player, image + 0x4bd914); U32(player + 4, 0x2200000 + (uint)index * 0x100);
            U32(player + 8, name); Text(name, index == 0 ? "Dyspro" : "Computer " + index);
            Bytes(player + 0xc, [bot ? (byte)1 : (byte)0]); U32(player + 0x20, (uint)index + 1);
            if (index == 0) U32(player + 0x24, 0x2031000);
        }
        public void Match()
        {
            U32(image + 0x5f3fb8, 0x2300000); U32(Session + 0xf0, 2); U32(PlayerAddress(0) + 0x28, Kingdom);
            U32(Kingdom + 0x240, Nation + 0x2000); U32(Kingdom + 0x23c, 0x2051000);
            U32(0x2051004, Faction + 0x2000); Id(Nation + 0x2000, "haroun"); Id(Faction + 0x2000, "council");
        }
        public void Id(uint descriptor, string id) { U32(descriptor + 8, descriptor + 0x100); Text(descriptor + 0x100, id); }
        private void Text(uint address, string text) => Bytes(address, Encoding.Unicode.GetBytes(text + '\0'));
        public void U32(uint address, uint value) => Bytes(address, BitConverter.GetBytes(value));
        private void Bytes(uint address, byte[] bytes) { for (var i = 0; i < bytes.Length; i++) data[address + (uint)i] = bytes[i]; }
        public byte[] Read(uint address, int count)
        {
            if (address < 0x10000 || count is < 1 or > 16384) throw new IOException();
            return Enumerable.Range(0, count).Select(i => data.GetValueOrDefault(address + (uint)i)).ToArray();
        }
    }
}
