using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;

// Beta city assistant. Install only into the launcher's own fresh, verified game.
internal static class PawAssistantRuntime
{
    private const uint Hook = 0x4A17F0, Original = 0x109FA6, Entry = 0x1000;
    private const int Size = 0x20000;
    private static readonly uint[] Sites = { Hook, 0x48A6D4, 0x48A6BC, 0x48A6C4, 0x48A718, 0x5059FC, 0x5059EC, 0x2A4B14, 0x2A4B5D, 0x496F10 };
    private static readonly uint[] Originals = { Original, 0xBB184, 0xBB71E, 0xBB205, 0xBB238, 0x2AB372, 0x2AB356, 0x2A4D12, 0x2A4DA5 };
    private static readonly uint[] Targets = { 0x2000, 0x1200, 0x1600, 0x1700, 0x1900, 0x4800, 0x4B00, 0x4C00, 0x4D00 };
    private const string OriginalLayout = "UI/Game/city_management_display.tgi::CityManagement";
    private const string EnglishLayout = "UI/Game/paw_city_en.tgi::CityManagement";
    private const string RussianLayout = "UI/Game/paw_city_ru.tgi::CityManagement";
    private static NativeMemory memory;
    private static uint state, image;
    private static uint lastReported;
    private static uint lastUiRevision, lastUiLoads;
    private static Action<string> logger;
    private static bool probeRequested, probeDone;
    private static uint activeSince;
    private static string lastSnapshotSummary;
    private static readonly CityPlanner planner = new CityPlanner(Environment.TickCount);
    private static uint requestSerial, pendingRequest, lastSnapshotSerial, requestEpoch;
    private static string lastStatusText, lastStatusTooltip;
    private static uint statusSequence;
    private static bool russianUi;

    internal static void EnableNoticeProbe() { probeRequested = true; }

    private static byte[] Resource(string name)
    {
        using (Stream input = Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
        {
            if (input == null) throw new InvalidDataException("Missing assistant resource: " + name);
            using (MemoryStream output = new MemoryStream()) { input.CopyTo(output); return output.ToArray(); }
        }
    }

    internal static byte[] Relocate(uint module, uint cave)
    {
        byte[] bytes = Resource("AssistantPayload");
        if (bytes.Length != Size) throw new InvalidDataException("Assistant payload size mismatch.");
        using (BinaryReader reader = new BinaryReader(new MemoryStream(Resource("AssistantFixups"))))
        {
            uint count = reader.ReadUInt32();
            if (count == 0 || count > 4096 || reader.BaseStream.Length != 4 + 12 * count)
                throw new InvalidDataException("Invalid assistant relocation count.");
            HashSet<uint> seen = new HashSet<uint>();
            for (uint i = 0; i < count; i++)
            {
                uint kind = reader.ReadUInt32(), offset = reader.ReadUInt32(), value = reader.ReadUInt32();
                if (offset < Entry || offset > Size - 4 || !seen.Add(offset))
                    throw new InvalidDataException("Invalid assistant relocation offset.");
                uint result;
                if (kind == 1 && value < 0x700000) result = unchecked(module + value);
                else if (kind == 2 && value < Size) result = unchecked(cave + value);
                else if (kind == 3 && value < 0x700000) result = unchecked(module + value - (cave + offset + 4));
                else throw new InvalidDataException("Invalid assistant relocation target.");
                Array.Copy(BitConverter.GetBytes(result), 0, bytes, offset, 4);
            }
        }
        return bytes;
    }

    internal static uint InstallPayload(IMemory mem, uint module, uint signal, bool russian)
    {
        // A zero signal preserves native desync handling; city automation is independent.
        string layout = russian ? RussianLayout : EnglishLayout;
        byte[][] originals = new byte[Sites.Length][];
        for (int i = 0; i < Sites.Length; i++)
        {
            originals[i] = i < Originals.Length ? BitConverter.GetBytes(module + Originals[i]) : Encoding.Unicode.GetBytes(OriginalLayout + "\0");
            TerrainPatch.Expect(mem, module + Sites[i], originals[i]);
        }
        uint cave = mem.Allocate(Size);
        int attempted = 0;
        try
        {
            byte[] bytes = Relocate(module, cave);
            Array.Copy(BitConverter.GetBytes(signal), 0, bytes, 8, 4);
            Array.Copy(BitConverter.GetBytes(russian ? 1 : 0), 0, bytes, 32, 4);
            mem.Write(cave, bytes);
            // State stays RW. Executable code is on a separate RX page.
            mem.MakeExecutable(cave + Entry, 0x7000);
            mem.Flush(cave + Entry, 0x7000);
            for (int i = 0; i < Sites.Length; i++)
            {
                TerrainPatch.Expect(mem, module + Sites[i], originals[i]);
                byte[] replacement = i < Targets.Length ? BitConverter.GetBytes(cave + Targets[i]) : new byte[originals[i].Length];
                if (i == Targets.Length) Array.Copy(Encoding.Unicode.GetBytes(layout + "\0"), replacement, Encoding.Unicode.GetByteCount(layout + "\0"));
                attempted = i + 1;
                mem.WriteCode(module + Sites[i], replacement);
                mem.Flush(module + Sites[i], replacement.Length);
                TerrainPatch.Expect(mem, module + Sites[i], replacement);
            }
            return cave;
        }
        catch
        {
            for (int i = attempted - 1; i >= 0; i--)
            {
                // Never free executable memory until the vtable is restored.
                // A rollback error propagates to the fresh-process startup abort.
                mem.WriteCode(module + Sites[i], originals[i]);
                mem.Flush(module + Sites[i], originals[i].Length);
                TerrainPatch.Expect(mem, module + Sites[i], originals[i]);
            }
            mem.Free(cave);
            throw;
        }
    }

    internal static void Install(Process game, IntPtr module, IntPtr signal, string root, Action<string> log)
    {
        if (memory != null || game.HasExited || module != ReleaseStartup.VerifiedImage)
            throw new InvalidOperationException("Assistant startup identity check failed.");
        image = unchecked((uint)module.ToInt32());
        memory = new NativeMemory(game.Id);
        memory.Suspend();
        try
        {
            bool russian = File.Exists(Path.Combine(root, @"Local_ru\Localization\strings_ui_K2.tgi"));
            russianUi = russian;
            GuardData(root);
            state = InstallPayload(memory, image, unchecked((uint)signal.ToInt32()), russian);
            memory.Write(state, BitConverter.GetBytes(Environment.TickCount));
            logger = log;
            log("ASSISTANT beta installed; cityOrders=true; cooldown=300000ms; nativeNotice=" + (signal != IntPtr.Zero) + ".");
        }
        finally { memory.Resume(); }
    }

    internal static void GuardData(string root)
    {
        // Both languages are required so later localization switches remain offline.
        foreach (string file in new[] { @"data\UI\Game\paw_city_en.tgi", @"data\UI\Game\paw_city_ru.tgi" })
            if (!File.Exists(Path.Combine(root, file)))
                throw new FileNotFoundException("Missing city assistant layout: " + file);
    }

    internal static void Tick()
    {
        if (memory == null || state == 0) return;
        uint now = unchecked((uint)Environment.TickCount);
        memory.Write(state, BitConverter.GetBytes(now));
        uint count = BitConverter.ToUInt32(memory.Read(state + 24, 4), 0);
        if (count != lastReported)
        {
            lastReported = count;
            logger("ASSISTANT native notice emitted count=" + count + ".");
        }
        byte[] ui = memory.Read(state + 0x40, 0x50);
        uint revision = BitConverter.ToUInt32(ui, 0x14), loads = BitConverter.ToUInt32(ui, 0x1c);
        if (revision != lastUiRevision || loads != lastUiLoads)
        {
            lastUiRevision = revision; lastUiLoads = loads;
            logger("ASSISTANT UI enabled=" + BitConverter.ToUInt32(ui, 0) + " reserve=" + BitConverter.ToUInt32(ui, 4)
                + " inputValid=" + BitConverter.ToUInt32(ui, 0x18) + " revision=" + revision + " loads=" + loads + ".");
        }
        if (BitConverter.ToUInt32(ui, 0x40) != 0)
            PublishStatus(BitConverter.ToUInt32(ui, 0x48) != 0
                ? T("Введите целое число: 0–9999999", "Enter a whole number: 0–9999999")
                : T("Изменение запаса: Enter — применить", "Editing reserve: Enter to apply"),
                T("Новые постройки приостановлены. Enter — применить; Esc или клик вне поля — отменить.",
                  "New orders paused. Enter applies; Esc or clicking outside cancels."));
        byte[] snapshot = memory.Read(state + 0x100, 0x180);
        uint serial = BitConverter.ToUInt32(snapshot, 0);
        uint cities = BitConverter.ToUInt32(snapshot, 0x1c), candidates = BitConverter.ToUInt32(snapshot, 0x20);
        if ((serial & 1) == 0 && BitConverter.ToUInt32(snapshot, 0x28) == 1 && cities <= 256 && candidates <= 512)
        {
            byte[] records = memory.Read(state + 0x8000, (int)candidates * 128);
            byte[] cityRecords = memory.Read(state + 0x19000, (int)cities * 8);
            if (BitConverter.ToUInt32(memory.Read(state + 0x100, 4), 0) == serial)
            {
                string summary = "epoch=" + BitConverter.ToUInt32(snapshot, 4) + " cities=" + cities + " candidates=" + candidates;
                if (summary != lastSnapshotSummary)
                {
                    lastSnapshotSummary = summary;
                    logger("ASSISTANT OBSERVER " + summary + " gold=" + BitConverter.ToSingle(snapshot, 0x14));
                    for (int i = 0; i < cities; i++) logger("ASSISTANT CITY id=" + BitConverter.ToUInt32(cityRecords, i * 8) + " busy=" + BitConverter.ToUInt32(cityRecords, i * 8 + 4));
                    for (int i = 0; i < Math.Min(candidates, 20); i++)
                    {
                        int o = i * 128;
                        logger("ASSISTANT CANDIDATE city=" + BitConverter.ToUInt32(records, o) + " actor=" + BitConverter.ToUInt32(records, o + 4)
                            + " data=" + BitConverter.ToUInt32(records, o + 8).ToString("X8") + " kind=" + BitConverter.ToUInt32(records, o + 12)
                            + " cost=" + BitConverter.ToSingle(records, o + 16) + " delta=" + string.Join(",", Enumerable.Range(0, (int)BitConverter.ToUInt32(snapshot, 0x18)).Select(r => BitConverter.ToSingle(records, o + 20 + r * 4).ToString()).ToArray()));
                    }
                }
                if (serial != lastSnapshotSerial)
                {
                    lastSnapshotSerial = serial;
                    Plan(snapshot, ui, records, cityRecords);
                }
            }
        }
        // An explicitly requested local QA mode tests only presentation, not a
        // real desync and never changes the world or the sync failure counter.
        if (probeRequested && !probeDone)
        {
            bool active = BitConverter.ToUInt32(memory.Read(image + 0x5F9218, 4), 0) == 2
                && BitConverter.ToUInt32(memory.Read(image + 0x5F3FB8, 4), 0) != 0;
            if (!active) activeSince = 0;
            else if (activeSince == 0) activeSince = now;
            else if (unchecked(now - activeSince) >= 5000)
            {
                probeDone = true;
                memory.Write(state + 36, BitConverter.GetBytes(1));
                logger("ASSISTANT QA requested a presentation-only notice; no desync was induced.");
            }
        }
    }

    private static void Plan(byte[] header, byte[] ui, byte[] records, byte[] cityRecords)
    {
        int resourceCount = (int)BitConverter.ToUInt32(header, 0x18);
        if (resourceCount < 1 || resourceCount > 16) return;
        CityPlanner.Snapshot s = new CityPlanner.Snapshot {
            Epoch = BitConverter.ToUInt32(header, 4), Time = BitConverter.ToSingle(header, 0x10),
            Gold = BitConverter.ToSingle(header, 0x14), Reserve = BitConverter.ToUInt32(ui, 4),
            Enabled = BitConverter.ToUInt32(ui, 0) == 1,
            Valid = BitConverter.ToUInt32(ui, 0x18) == 1 && unchecked((uint)Environment.TickCount - BitConverter.ToUInt32(ui,0x30)) >= 1000,
            Cities = Enumerable.Range(0, cityRecords.Length / 8).Select(i => BitConverter.ToUInt32(cityRecords,i*8)).ToArray(),
            Income = Enumerable.Range(0,resourceCount).Select(i => BitConverter.ToSingle(header,0x100+i*4)).ToArray(),
            Candidates = Enumerable.Range(0,records.Length / 128).Select(i => new CityPlanner.Candidate {
                City=BitConverter.ToUInt32(records,i*128), Actor=BitConverter.ToUInt32(records,i*128+4),
                CityAddress=BitConverter.ToUInt32(records,i*128+88),
                Data=BitConverter.ToUInt32(records,i*128+8), Kind=BitConverter.ToUInt32(records,i*128+12),
                Cost=BitConverter.ToSingle(records,i*128+16),
                Delta=Enumerable.Range(0,resourceCount).Select(j=>BitConverter.ToSingle(records,i*128+20+j*4)).ToArray()
            }).ToArray()
        };
        for (int i=0;i<s.Cities.Length;i++) if (BitConverter.ToUInt32(cityRecords,i*8+4)!=0) s.Busy.Add(s.Cities[i]);
        if (pendingRequest != 0)
        {
            byte[] reply = memory.Read(state + 0x15c, 8);
            if (BitConverter.ToUInt32(reply,4) == pendingRequest)
            {
                uint result=BitConverter.ToUInt32(reply,0);
                if (requestEpoch == s.Epoch) planner.Reply(result==1,s.Time);
                logger("ASSISTANT ORDER reply="+pendingRequest+" result="+result+" gameTime="+s.Time);
                pendingRequest=0;
            }
            // The native mailbox must acknowledge/cancel the old epoch first.
            else return;
        }
        CityPlanner.Decision decision = planner.Update(s);
        if (BitConverter.ToUInt32(ui, 0x40) == 0) ShowPlannerStatus(s);
        if (decision.Kind == CityPlanner.DecisionKind.Fault)
        {
            logger("ASSISTANT SAFETY STOP " + decision.Reason);
            memory.Write(state + 0x68, BitConverter.GetBytes(0));
            memory.Write(state + 0x64, BitConverter.GetBytes(1));
        }
        else if (decision.Kind == CityPlanner.DecisionKind.Submit)
        {
            CityPlanner.Candidate c = decision.Candidate;
            byte[] request=new byte[24];
            uint[] fields={s.Epoch,c.City,c.Actor,c.Data,c.Kind};
            for(int i=0;i<fields.Length;i++) Array.Copy(BitConverter.GetBytes(fields[i]),0,request,i*4,4);
            Array.Copy(BitConverter.GetBytes(s.Time),0,request,20,4);
            memory.Write(state+0x144,request);
            requestSerial++; if(requestSerial==0) requestSerial++;
            requestEpoch=s.Epoch; pendingRequest=requestSerial;
            memory.Write(state+0x140,BitConverter.GetBytes(requestSerial));
            logger("ASSISTANT ORDER request="+requestSerial+" city="+c.City+" actor="+c.Actor+" kind="+c.Kind+" cost="+c.Cost+" gold="+s.Gold+" reserve="+s.Reserve+" time="+s.Time);
        }
    }

    private static string T(string ru, string en) { return russianUi ? ru : en; }
    private static string ReadGameString(uint address)
    {
        if (address < 0x10000) return "";
        uint count = BitConverter.ToUInt32(memory.Read(address - 12, 4), 0);
        if (count == 0 || count > 128) return "";
        return Encoding.Unicode.GetString(memory.Read(address, (int)count * 2)).Replace("\0", "");
    }
    private static uint Pointer(uint address) { return BitConverter.ToUInt32(memory.Read(address, 4), 0); }
    private static string CityName(CityPlanner.Candidate c)
    {
        uint actor = c.CityAddress;
        if (actor == 0 || Pointer(actor + 0x14) != c.City) return T("Город", "City");
        uint settlement = Pointer(actor + 0x98);
        if (settlement != 0) { uint main = Pointer(settlement + 0x14); if (main != 0) actor = main; }
        string name = ReadGameString(Pointer(actor + 0xe0));
        return name.Length > 0 ? name : ReadGameString(Pointer(Pointer(actor + 4) + 0x10));
    }
    private static void ShowPlannerStatus(CityPlanner.Snapshot s)
    {
        string text;
        switch (planner.Status)
        {
            case CityPlanner.StatusKind.Off: text=T("Автоулучшение выключено", "Auto-upgrade off"); break;
            case CityPlanner.StatusKind.Paused: text=T("Пауза", "Paused"); break;
            case CityPlanner.StatusKind.Gold:
                text=T("Ожидание золота: ещё ", "Waiting for gold: ") + Math.Max(0, Math.Ceiling((double)s.Reserve + planner.Next.Cost - s.Gold)).ToString("0"); break;
            case CityPlanner.StatusKind.Pending: text=T("Передача приказа на строительство", "Sending construction order"); break;
            case CityPlanner.StatusKind.Busy: text=T("Все города заняты", "All cities busy"); break;
            case CityPlanner.StatusKind.NoCities: text=T("Нет доступных городов", "No available cities"); break;
            case CityPlanner.StatusKind.NoChoices: text=T("Нет доступных улучшений", "No available improvements"); break;
            case CityPlanner.StatusKind.Fault: text=T("Остановлено: проверьте город", "Stopped: check the city"); break;
            default: text=T("Проверка городов…", "Checking cities…"); break;
        }
        string tooltip=T("Приоритет: дефицит ресурсов → золото → другие улучшения.", "Priority: resource deficit → gold → other improvements.");
        CityPlanner.Candidate next = planner.Next;
        if (next != null)
        {
            string city=T("Город", "City"), building=T("Постройка", "Building");
            try { string n=CityName(next); if(n.Length>0) city=n; n=ReadGameString(Pointer(next.Data+0x10)); if(n.Length>0) building=n; }
            catch { /* A city can disappear while reading presentation hints. */ }
            tooltip=city+" — "+building+"\n"+T("Стоимость: ", "Cost: ")+next.Cost.ToString("0.##")
                +T(" · Запас: ", " · Reserve: ")+s.Reserve+"\n"+tooltip;
        }
        PublishStatus(text,tooltip);
    }
    private static byte[] StatusBytes(string text, int capacity)
    {
        if (text.Length >= capacity) text=text.Substring(0,capacity-1);
        byte[] data=new byte[capacity*2]; Encoding.Unicode.GetBytes(text,0,text.Length,data,0); return data;
    }
    private static void PublishStatus(string text,string tooltip)
    {
        if(text==lastStatusText && tooltip==lastStatusTooltip) return;
        memory.Write(state+0x98,BitConverter.GetBytes(++statusSequence));
        memory.Write(state+0x1a000,StatusBytes(text,256));
        memory.Write(state+0x1a400,StatusBytes(tooltip,512));
        memory.Write(state+0x98,BitConverter.GetBytes(++statusSequence));
        lastStatusText=text;lastStatusTooltip=tooltip;
    }

    internal static int SelfTest()
    {
        if (!Resource("AssistantPayload").SequenceEqual(Relocate(0x460000, 0x10000000)))
            throw new Exception("Identity relocation mismatch.");
        int assertions = 1;
        int operations = 0;
        foreach (uint module in new uint[] { 0x460000, 0x650000, 0x12000000 })
        {
            FakeMemory mem = new FakeMemory(module);
            Seed(mem, module);
            uint cave = InstallPayload(mem, module, 0x23456000, true);
            operations = mem.Operations;
            TerrainPatch.Expect(mem, module + Hook, BitConverter.GetBytes(cave + Targets[0]));
            TerrainPatch.Expect(mem, cave + 8, BitConverter.GetBytes(0x23456000));
            TerrainPatch.Expect(mem, cave + 32, BitConverter.GetBytes(1));
            assertions += 3;
        }
        foreach (bool russian in new[] { false, true })
        {
            FakeMemory noBypass = new FakeMemory(0x460000);
            Seed(noBypass, 0x460000);
            uint cave = InstallPayload(noBypass, 0x460000, 0, russian);
            TerrainPatch.Expect(noBypass, cave + 8, BitConverter.GetBytes(0));
            TerrainPatch.Expect(noBypass, cave + 32, BitConverter.GetBytes(russian ? 1 : 0));
            assertions += 2;
        }
        FakeMemory wrong = new FakeMemory(0x460000);
        wrong.Seed(0x460000 + Hook, new byte[4]);
        try { InstallPayload(wrong, 0x460000, 1, false); throw new Exception("Invalid hook accepted."); }
        catch (InvalidOperationException) { assertions++; }
        for (int failAt = 1; failAt <= operations; failAt++)
        {
            FakeMemory failing = new FakeMemory(0x460000);
            Seed(failing, 0x460000);
            failing.FailAt = failAt;
            bool rejected = false;
            try { InstallPayload(failing, 0x460000, 0x23456000, false); }
            catch (IOException) { rejected = true; }
            if (!rejected || failing.Allocated) throw new Exception("Install failure did not clean up at " + failAt);
            TerrainPatch.Expect(failing, 0x460000 + Hook, BitConverter.GetBytes(0x460000 + Original));
            assertions += 3;
        }
        Console.WriteLine("ASSISTANT_INSTALL_PASS " + assertions + " checks; offline only");
        return 0;
    }

    private static void Seed(FakeMemory mem, uint module)
    {
        for (int i = 0; i < Sites.Length; i++)
            mem.Seed(module + Sites[i], i < Originals.Length ? BitConverter.GetBytes(module + Originals[i]) : Encoding.Unicode.GetBytes(OriginalLayout + "\0"));
    }
}
