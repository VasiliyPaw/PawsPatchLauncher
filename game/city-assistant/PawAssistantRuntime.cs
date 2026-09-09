using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;

// Beta city assistant. Install only into the launcher's own fresh, verified game.
internal static class PawAssistantRuntime
{
    private const uint Hook = 0x4A17F0, Original = 0x109FA6, Entry = 0x1000;
    private const int Size = 0x30000;
    private static readonly uint[] Sites = { Hook, 0x48A6D4, 0x48A6BC, 0x48A6C4, 0x48A718, 0x5059FC, 0x5059EC, 0x2A4B14, 0x2A4B5D, 0x496F10, 0x188215, 0x1883de };
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
    private static Process gameProcess;
    private static CityPolicy policy = new CityPolicy();
    private static string policyPath;
    private static uint settingsRequest, policyEpoch;
    private static uint floorRevision;
    private static bool floorsReady;
    private static volatile bool settingsOpen;
    private static CityPolicy settingsResult;
    private static uint settingsEpoch;
    private static readonly object settingsLock = new object();
    private static CitySettingsForm.View settingsView;
    private static readonly Dictionary<uint,string> cityNames = new Dictionary<uint,string>();
    private static readonly Dictionary<uint,Tuple<string,string,int>> dataInfo = new Dictionary<uint,Tuple<string,string,int>>();
    private static readonly Dictionary<string,CitySettingsForm.BranchOption> branchOptions = new Dictionary<string,CitySettingsForm.BranchOption>();

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
            originals[i] = OriginalBytes(i,module);
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
                byte[] replacement;
                if(i<Targets.Length) replacement=BitConverter.GetBytes(cave+Targets[i]);
                else if(i==Targets.Length)
                { replacement=new byte[originals[i].Length];Array.Copy(Encoding.Unicode.GetBytes(layout+"\0"),replacement,Encoding.Unicode.GetByteCount(layout+"\0")); }
                else
                {
                    replacement=Enumerable.Repeat((byte)0x90,originals[i].Length).ToArray();replacement[0]=0xe9;
                    Array.Copy(BitConverter.GetBytes(unchecked(cave+(i==10?0x5400u:0x5500u)-(module+Sites[i]+5))),0,replacement,1,4);
                }
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
            gameProcess = game;
            policyPath=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"PawsPatch","city-policy.ini");
            try {
                policy=CityPolicy.LoadPreferred(policyPath,Path.Combine(Path.GetDirectoryName(policyPath),"city-policy-test-v2.ini"));
                if(!File.Exists(policyPath)) policy.Save(policyPath);
            } catch(Exception ex) { log("ASSISTANT preference load: "+ex.Message); }
            InitializeNativePolicy();
            memory.Write(state, BitConverter.GetBytes(Environment.TickCount));
            logger = log;
            log("ASSISTANT beta installed; cityOrders=true; cooldown=300000ms; nativeNotice=" + (signal != IntPtr.Zero) + ".");
        }
        finally { memory.Resume(); }
    }

    internal static void GuardData(string root)
    {
        // Both languages are required so later localization switches remain offline.
        foreach (string file in new[] { @"data\UI\Game\paw_city_en.tgi", @"data\UI\Game\paw_city_ru.tgi", @"data\Localization\paw_city_policy.tgi" })
            if (!File.Exists(Path.Combine(root, file)))
                throw new FileNotFoundException("Missing city assistant layout: " + file);
    }

    internal static void Tick()
    {
        if (memory == null || state == 0) return;
        uint now = unchecked((uint)Environment.TickCount);
        memory.Write(state, BitConverter.GetBytes(now));
        floorsReady=ReadNativeFloors();
        if(!settingsOpen)
        {
            CityPolicy result=null;
            lock(settingsLock) {result=settingsResult;settingsResult=null;}
            if(result!=null)
            {
                if(settingsEpoch!=policyEpoch) result.ClearCities();
                // This dialog no longer edits floors. Never replace newer F1
                // values with the copy captured when the dialog was opened.
                result.Floors=(float[])policy.Floors.Clone();
                policy=result;
                try { policy.Save(policyPath); logger("ASSISTANT preferences applied and saved"); }
                catch(Exception ex) {logger("ASSISTANT preferences applied; save failed: "+ex.Message);}
            }
            // Do not release a new native click's lock before observing it.
            if(settingsRequest!=0 && Pointer(state+0xac)==settingsRequest)
                memory.Write(state+0xb4,BitConverter.GetBytes(0));
        }
        uint count = BitConverter.ToUInt32(memory.Read(state + 24, 4), 0);
        if (count != lastReported)
        {
            lastReported = count;
            logger("ASSISTANT native notice emitted count=" + count + ".");
        }
        uint requested=Pointer(state+0xac);
        if(requested!=settingsRequest && settingsView!=null)
        {
            settingsRequest=requested;
            if(!settingsOpen) OpenSettings();
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
                ? (BitConverter.ToUInt32(ui,0x40)==1 ? T("Введите целое число: 0–9999999", "Enter a whole number: 0–9999999") : T("Введите целое число: 0–9999", "Enter a whole number: 0–9999"))
                : T("Изменение порога: Enter — применить", "Editing target: Enter to apply"),
                T("Новые постройки приостановлены. Enter — применить; Esc или клик вне поля — отменить.",
                  "New orders paused. Enter applies; Esc or clicking outside cancels."));
        byte[] snapshot = memory.Read(state + 0x100, 0x180);
        uint serial = BitConverter.ToUInt32(snapshot, 0);
        uint cities = BitConverter.ToUInt32(snapshot, 0x1c), candidates = BitConverter.ToUInt32(snapshot, 0x20);
        uint workCount = BitConverter.ToUInt32(snapshot, 0x2c);
        if ((serial & 1) == 0 && BitConverter.ToUInt32(snapshot, 0x28) == 1 && cities <= 256 && candidates <= 512 && workCount <= 512)
        {
            byte[] records = memory.Read(state + 0x8000, (int)candidates * 128);
            byte[] cityRecords = memory.Read(state + 0x19000, (int)cities * 8);
            byte[] construction = memory.Read(state + 0x20000, (int)workCount * 128);
            byte[] forecast = memory.Read(state + 0x1b020, 0x40);
            if (BitConverter.ToUInt32(memory.Read(state + 0x100, 4), 0) == serial)
            {
                string summary = "epoch=" + BitConverter.ToUInt32(snapshot, 4) + " cities=" + cities + " candidates=" + candidates + " construction=" + workCount;
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
                    Plan(snapshot, ui, records, cityRecords, construction, forecast);
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

    private static void Plan(byte[] header, byte[] ui, byte[] records, byte[] cityRecords, byte[] construction, byte[] forecast)
    {
        int resourceCount = (int)BitConverter.ToUInt32(header, 0x18);
        if (!CityResourceOrder.Supported(resourceCount)) return;
        CityPlanner.Snapshot s = new CityPlanner.Snapshot {
            Epoch = BitConverter.ToUInt32(header, 4), Time = BitConverter.ToSingle(header, 0x10),
            Gold = BitConverter.ToSingle(header, 0x14), Reserve = BitConverter.ToUInt32(ui, 4),
            Enabled = BitConverter.ToUInt32(ui, 0) == 1,
            Valid = BitConverter.ToUInt32(ui, 0x18) == 1 && unchecked((uint)Environment.TickCount - BitConverter.ToUInt32(ui,0x30)) >= 1000,
            Cities = Enumerable.Range(0, cityRecords.Length / 8).Select(i => BitConverter.ToUInt32(cityRecords,i*8)).ToArray(),
            Income = CityResourceOrder.Read(header,0x100,resourceCount),
            Candidates = Enumerable.Range(0,records.Length / 128).Select(i => new CityPlanner.Candidate {
                City=BitConverter.ToUInt32(records,i*128), Actor=BitConverter.ToUInt32(records,i*128+4),
                CityAddress=BitConverter.ToUInt32(records,i*128+88),
                Data=BitConverter.ToUInt32(records,i*128+8), Kind=BitConverter.ToUInt32(records,i*128+12),
                Cost=BitConverter.ToSingle(records,i*128+16),
                Delta=CityResourceOrder.Read(records,i*128+20,resourceCount)
            }).ToArray()
        };
        for (int i=0;i<s.Cities.Length;i++) if (BitConverter.ToUInt32(cityRecords,i*8+4)!=0) s.Busy.Add(s.Cities[i]);
        if(s.Epoch!=policyEpoch)
        {
            policyEpoch=s.Epoch;policy.ClearCities();cityNames.Clear();dataInfo.Clear();branchOptions.Clear();
        }
        s.Policy=policy;
        s.Valid=s.Valid && !settingsOpen && floorsReady;
        s.UnknownConstruction=BitConverter.ToUInt32(header,0x30)!=1;
        s.Forecast=(float[])s.Income.Clone();
        s.GoalIncome=(float[])s.Income.Clone();
        for(int i=0;i<Math.Min(5,resourceCount);i++)
        {
            s.Forecast[i]+=BitConverter.ToSingle(forecast,i*4);
            s.GoalIncome[i]+=BitConverter.ToSingle(forecast,0x20+i*4);
        }
        s.Construction=Enumerable.Range(0,construction.Length/128).Select(i=>new CityPlanner.Candidate {
            City=BitConverter.ToUInt32(construction,i*128), Actor=BitConverter.ToUInt32(construction,i*128+4),
            Data=BitConverter.ToUInt32(construction,i*128+8), Kind=BitConverter.ToUInt32(construction,i*128+12)
        }).ToArray();
        // Names must not depend on having an eligible construction candidate:
        // finished or besieged cities still appear in the exceptions page.
        try
        {
            uint kingdom=BitConverter.ToUInt32(header,0x0c);
            uint total=Pointer(kingdom+0x2e0), array=Pointer(kingdom+0x2dc);
            if(total<=256 && array!=0)
            {
                byte[] pointers=memory.Read(array,(int)total*4);
                for(int i=0;i<total;i++)
                {
                    uint actor=BitConverter.ToUInt32(pointers,i*4);
                    if(actor==0) continue;
                    uint id=Pointer(actor+0x14);
                    if(s.Cities.Contains(id))
                    {
                        string name=CityName(actor,id);
                        if(name.Length>0) cityNames[id]=name;
                    }
                }
            }
        }
        catch { /* Keep already verified names if the world changed mid-read. */ }
        for(int i=0;i<s.Candidates.Length;i++)
        {
            CityPlanner.Candidate c=s.Candidates[i];
            try
            {
                uint old=BitConverter.ToUInt32(records,i*128+84);
                var source=DataInfo(old);var target=DataInfo(c.Data);
                c.Name=target.Item2;c.Target=target.Item1;c.SourceName=source.Item2;c.Family=source.Item1;c.BranchCount=source.Item3;
                uint component=Pointer(c.CityAddress+0x98), center=component==0?0:Pointer(component+0x14);
                c.IsCityCenter=c.Kind==21 && center!=0 && Pointer(center+0x14)==c.Actor;
                string cityName=CityName(c.CityAddress,c.City);
                if(cityName.Length>0) cityNames[c.City]=cityName;
                if(c.Kind==21)
                    branchOptions[c.Family+":"+c.Target]=new CitySettingsForm.BranchOption {Family=c.Family,Source=c.SourceName,Target=c.Target,Name=c.Name,Effects=CitySettingsForm.DeltaText(c.Delta,russianUi)};
            }
            catch { c.BranchCount=int.MaxValue; c.Family="unavailable"; c.Target="unavailable"; }
        }
        foreach(uint city in cityNames.Keys.Where(c=>!s.Cities.Contains(c)).ToArray())cityNames.Remove(city);
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
        settingsView=new CitySettingsForm.View {Epoch=s.Epoch,Income=(float[])s.Income.Clone(),Status=lastStatusText+"\n"+lastStatusTooltip,
            Cities=s.Cities.ToDictionary(c=>c,c=>cityNames.ContainsKey(c)?cityNames[c]:T("Город ","City ")+c),Options=branchOptions.Values.ToArray()};
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
            logger("ASSISTANT ORDER request="+requestSerial+" city="+c.City+" actor="+c.Actor+" kind="+c.Kind+" cost="+c.Cost+" gold="+s.Gold+" reserve="+s.Reserve+" time="+s.Time
                +" target="+c.Target+" source="+c.Family+" reason="+planner.Explanation+" income=["+Numbers(s.Income)+"] delta=["+Numbers(c.Delta)+"] floors=["+Numbers(Enumerable.Range(0,5).Select(policy.Floor).ToArray())+"] construction="+s.Construction.Length+" safe=["+Numbers(s.Forecast)+"] goals=["+Numbers(s.GoalIncome)+"]");
        }
    }

    private static string T(string ru, string en) { return russianUi ? ru : en; }
    private static string Numbers(float[] values) { return string.Join(";",values.Select(v=>v.ToString("0.###",System.Globalization.CultureInfo.InvariantCulture)).ToArray()); }
    private static Tuple<string,string,int> DataInfo(uint data)
    {
        // New construction has no previous building definition.
        if(data==0) return Tuple.Create("","",0);
        Tuple<string,string,int> info;
        if(dataInfo.TryGetValue(data,out info)) return info;
        string id=CityPolicy.DefinitionKey(data,Pointer,ReadGameString), name=ReadGameString(Pointer(data+0x10));
        HashSet<uint> visited=new HashSet<uint>();uint node=Pointer(data+0x4c0);int branches=0;
        while(node!=0 && visited.Add(node) && branches<512) {branches++;node=Pointer(node+4);}
        info=Tuple.Create(id,name.Length>0?name:T("Постройка ","Building ")+id,branches);dataInfo[data]=info;return info;
    }
    private static string EffectText(CityPlanner.Snapshot s,CityPlanner.Candidate c)
    {
        return string.Join(" · ",Enumerable.Range(0,Math.Min(5,c.Delta.Length)).Where(i=>Math.Abs(c.Delta[i])>.0001f)
            .Select(i=>CitySettingsForm.ResourceName(i,russianUi)+" "+s.Income[i].ToString("0.##")+" → "+(s.Income[i]+c.Delta[i]).ToString("0.##")
                +" ("+c.Delta[i].ToString("+0.##;-0.##;0")+")").ToArray());
    }
    private static void InitializeNativePolicy()
    {
        memory.Write(state+0xb8,BitConverter.GetBytes(0));
        for(int i=1;i<5;i++) policy.Floors[i]=(float)Math.Min(9999,Math.Ceiling(policy.Floor(i)));
        byte[] floors=new byte[20];for(int i=0;i<5;i++)Array.Copy(BitConverter.GetBytes(policy.Floor(i)),0,floors,i*4,4);
        memory.Write(state+0x1b000,floors);
        // Construction aggregates are owned by the native snapshot, never
        // cleared asynchronously while the dispatcher is checking resources.
        memory.Write(state+0xb8,BitConverter.GetBytes(1));
    }
    private static bool ReadNativeFloors()
    {
        uint revision=Pointer(state+0x1c020);
        if((revision&1)!=0) return false;
        if(revision==floorRevision) return true;
        byte[] values=memory.Read(state+0x1b000,20);
        if(Pointer(state+0x1c020)!=revision) return false;
        float[] floors=new float[5];
        for(int i=1;i<5;i++)
        {
            float value=BitConverter.ToSingle(values,i*4);
            if(!CityPlanner.Finite(value) || value<0 || value>9999 || value!=Math.Floor(value)) return false;
            floors[i]=value;
        }
        policy.Floors=floors;floorRevision=revision;
        // ACK only the coherent revision consumed above. A newer commit keeps
        // the final native gate locked until the next poll acknowledges it.
        memory.Write(state+0x1c024,BitConverter.GetBytes(revision));
        logger("ASSISTANT F1 income targets="+string.Join(",",floors.Skip(1).Select(v=>v.ToString("0")).ToArray()));
        try { policy.Save(policyPath); }
        catch(Exception ex) {logger("ASSISTANT F1 targets applied; save failed: "+ex.Message);}
        return true;
    }
    private sealed class GameWindow : IWin32Window {public IntPtr Handle {get;set;} }
    private static void OpenSettings()
    {
        settingsOpen=true;memory.Write(state+0xb4,BitConverter.GetBytes(1));
        logger("ASSISTANT settings requested");
        var view=settingsView;var copy=policy.Copy();settingsEpoch=view.Epoch;
        Thread thread=new Thread(delegate()
        {
            try
            {
                using(var form=new CitySettingsForm(copy,view,russianUi))
                using(var timer=new System.Windows.Forms.Timer {Interval=500})
                {
                    form.Shown+=delegate { logger("ASSISTANT settings shown"); };
                    timer.Tick+=delegate {try {if(gameProcess.HasExited)form.Close();}catch {form.Close();}};timer.Start();
                    gameProcess.Refresh();
                    if(form.ShowDialog(new GameWindow {Handle=gameProcess.MainWindowHandle})==DialogResult.OK)
                        lock(settingsLock) settingsResult=form.Result;
                }
            }
            catch(Exception ex) {logger("ASSISTANT settings window: "+ex.Message);}
            finally {logger("ASSISTANT settings closed");settingsOpen=false;}
        });
        thread.IsBackground=true;thread.SetApartmentState(ApartmentState.STA);thread.Start();
    }
    private static string ReadGameString(uint address)
    {
        if (address < 0x10000) return "";
        uint count = BitConverter.ToUInt32(memory.Read(address - 12, 4), 0);
        if (count == 0 || count > 128) return "";
        return Encoding.Unicode.GetString(memory.Read(address, (int)count * 2)).Replace("\0", "");
    }
    private static uint Pointer(uint address) { return BitConverter.ToUInt32(memory.Read(address, 4), 0); }
    private static string CityName(uint actor,uint id)
    {
        if (actor == 0 || Pointer(actor + 0x14) != id) return "";
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
            case CityPlanner.StatusKind.Protected: text=T("Нет улучшений по правилам защиты", "No improvements allowed by protection rules"); break;
            case CityPlanner.StatusKind.Construction: text=T("Уточнение расходов строек", "Checking construction commitments"); break;
            case CityPlanner.StatusKind.Editing: text=settingsOpen ? T("Настройка автоулучшения", "Configuring auto-upgrade") : T("Проверка параметров…", "Checking settings…"); break;
            case CityPlanner.StatusKind.Fault: text=T("Остановлено: проверьте город", "Stopped: check the city"); break;
            default: text=T("Проверка городов…", "Checking cities…"); break;
        }
        string tooltip=T("Приоритет: целевой доход ресурсов → золото. Новый или более глубокий минус запрещён.", "Priority: resource income targets → gold. Creating or worsening deficits is forbidden.");
        if(planner.Status==CityPlanner.StatusKind.Construction)tooltip=T("Не удалось надёжно прочитать расходы начатых строек. Новые приказы временно приостановлены для защиты порогов ресурсов.","Outstanding construction effects could not be read reliably. New orders are temporarily paused to protect resource targets.");
        if(planner.Status==CityPlanner.StatusKind.Protected)tooltip=T("Пороги защищены. Нет доступного полезного действия: лишние ресурсы без будущего прироста золота не наращиваются.","Targets are protected. No useful action is available: surplus resources are not increased without a future gold benefit.");
        CityPlanner.Candidate next = planner.Next;
        if (next != null)
        {
            string city=T("Город", "City"), building=T("Постройка", "Building");
            try { string n=CityName(next.CityAddress,next.City); if(n.Length>0) city=n; n=ReadGameString(Pointer(next.Data+0x10)); if(n.Length>0) building=n; }
            catch { /* A city can disappear while reading presentation hints. */ }
            tooltip=city+" — "+building+"\n"+T("Стоимость: ", "Cost: ")+next.Cost.ToString("0.##")
                +T(" · Запас: ", " · Reserve: ")+s.Reserve+"\n"+EffectText(s,next)+"\n"+tooltip;
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

    private static byte[] OriginalBytes(int index,uint module)
    {
        if(index<Originals.Length)return BitConverter.GetBytes(module+Originals[index]);
        if(index==9)return Encoding.Unicode.GetBytes(OriginalLayout+"\0");
        if(index==10)return new byte[]{0xb8}.Concat(BitConverter.GetBytes(module+0x43354e)).ToArray();
        return new byte[]{0x56,0x57,0x33,0xff,0x8b,0xf1};
    }
    private static void Seed(FakeMemory mem, uint module)
    {
        for (int i = 0; i < Sites.Length; i++)
            mem.Seed(module + Sites[i], OriginalBytes(i,module));
    }
}
