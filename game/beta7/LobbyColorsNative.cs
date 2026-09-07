using System;
using System.ComponentModel;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Security.Cryptography;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;

// Player-color prototype with a host-authoritative native request/decree pair.
// Original game executable remains unchanged on disk. All MP peers must use it.
internal static class PawLobbyColorsNative
{
    private const int PayloadSize = 249856;
    private const int PaletteCountOffset = 0x140;
    private const int PaletteSourceOffset = 0x1400;
    private const int PaletteEntrySize = 20;
    private const int PaletteStringsOffset = 0x6000;
    private const int PaletteStringsEnd = 0x10000;
    private const int MaxPaletteColors = 64;
    private const int MenuSiteIndex = 13;
    private static readonly int[] Sites = { 0x1267a5,0x12693f,0x1267b8,0x295516,0x295174,0x152b5a,0x152b86,0x9a0ee,0x2957ec,0x99f06,0x2958ce,0x23a122,0x15d6df,0x49E0E0 };
    private static readonly int[] Targets = { 106496,110592,114688,131072,135168,204800,208896,212992,212992,217088,217088,221184,233472,0 };
    private static readonly byte[] Opcodes = { 0xE9,0xE8,0xE9,0xE9,0xE9,0xE9,0xE9,0xE8,0xE8,0xE8,0xE8,0xE8,0xE8,0 };
    private static readonly byte[][] Expected = {
        new byte[] { 0x8B,0x4D,0xF4,0x8B,0xC7 },
        new byte[] { 0xE8,0x12,0x13,0x00,0x00 },
        new byte[] { 0x56,0x8B,0xF1,0x8D,0x8E,0x98,0x00,0x00,0x00 },
        new byte[] { 0x8B,0x43,0x20,0x89,0x45,0xF0 },
        new byte[] { 0xFF,0x73,0x20,0x8B,0xCF },
        new byte[] { 0xE9,0xFD,0x4B,0x01,0x00 },
        new byte[] { 0xE9,0xEF,0x4D,0x01,0x00 },
        new byte[] { 0xE8,0x51,0x02,0x00,0x00 },
        new byte[] { 0xE8,0x53,0x4B,0xE0,0xFF },
        new byte[] { 0xE8,0x13,0x03,0x00,0x00 },
        new byte[] { 0xE8,0x4B,0x49,0xE0,0xFF },
        new byte[] { 0xE8,0x92,0x4C,0xDF,0xFF },
        new byte[] { 0xE8,0xD2,0x68,0xEC,0xFF },
        Encoding.Unicode.GetBytes("UI/Menus/staging.tgi:StagingMenu\0")
    };
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool ReadProcessMemory(IntPtr p,IntPtr a,byte[] b,int n,out IntPtr done);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool WriteProcessMemory(IntPtr p,IntPtr a,byte[] b,int n,out IntPtr done);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern IntPtr VirtualAllocEx(IntPtr p,IntPtr a,int size,uint type,uint protection);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool VirtualFreeEx(IntPtr p,IntPtr a,int size,uint type);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool VirtualProtectEx(IntPtr p,IntPtr a,int n,uint protect,out uint old);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool FlushInstructionCache(IntPtr p,IntPtr a,int n);

    private static IntPtr Add(IntPtr value,int offset)
    { return new IntPtr(unchecked(value.ToInt64()+offset)); }

    private sealed class PaletteColor
    {
        public string Id;
        public string Name;
        public byte R, G, B;
    }

    private sealed class PaletteFile
    {
        public PaletteColor[] Colors;
        public string Sha256;
        public string Path;
    }

    private static PaletteFile LoadPalette()
    {
        string path=Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location),"paws_player_colors.ini");
        if(!File.Exists(path)) throw new FileNotFoundException("Missing player-only color palette",path);
        byte[] fileBytes=File.ReadAllBytes(path);
        var sections=new Dictionary<string,Dictionary<string,string>>(StringComparer.OrdinalIgnoreCase);
        var order=new List<string>();
        string current=null;
        int lineNumber=0;
        foreach(string sourceLine in File.ReadAllLines(path,Encoding.UTF8))
        {
            lineNumber++;
            string line=sourceLine.Trim();
            if(line.Length==0 || line.StartsWith(";") || line.StartsWith("#")) continue;
            if(line.StartsWith("[") && line.EndsWith("]"))
            {
                current=line.Substring(1,line.Length-2).Trim();
                if(!Regex.IsMatch(current,"^paws_[a-z0-9_]{1,48}$"))
                    throw new InvalidDataException("Invalid palette ID at line "+lineNumber);
                if(sections.ContainsKey(current)) throw new InvalidDataException("Duplicate palette ID "+current);
                sections[current]=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
                order.Add(current);
                continue;
            }
            int equals=line.IndexOf('=');
            if(current==null || equals<=0) throw new InvalidDataException("Invalid palette line "+lineNumber);
            string key=line.Substring(0,equals).Trim(), value=line.Substring(equals+1).Trim();
            if(sections[current].ContainsKey(key)) throw new InvalidDataException("Duplicate "+key+" in "+current);
            sections[current][key]=value;
        }
        if(order.Count<16 || order.Count>MaxPaletteColors)
            throw new InvalidDataException("Palette must contain 16 to "+MaxPaletteColors+" colors");
        bool russian=String.Equals(CultureInfo.CurrentUICulture.TwoLetterISOLanguageName,"ru",StringComparison.OrdinalIgnoreCase);
        var colors=new List<PaletteColor>();
        var rgbSeen=new HashSet<int>();
        foreach(string id in order)
        {
            Dictionary<string,string> values=sections[id];
            string nameRu, nameEn, rgb;
            if(!values.TryGetValue("name_ru",out nameRu) || !values.TryGetValue("name_en",out nameEn) || !values.TryGetValue("rgb",out rgb))
                throw new InvalidDataException("Palette section "+id+" requires name_ru, name_en and rgb");
            string[] parts=rgb.Split(',');
            int r,g,b;
            if(parts.Length!=3 || !Int32.TryParse(parts[0].Trim(),NumberStyles.Integer,CultureInfo.InvariantCulture,out r) ||
                !Int32.TryParse(parts[1].Trim(),NumberStyles.Integer,CultureInfo.InvariantCulture,out g) ||
                !Int32.TryParse(parts[2].Trim(),NumberStyles.Integer,CultureInfo.InvariantCulture,out b) ||
                r<0 || r>255 || g<0 || g>255 || b<0 || b>255)
                throw new InvalidDataException("Invalid RGB in "+id);
            int packed=(r<<16)|(g<<8)|b;
            if(!rgbSeen.Add(packed)) throw new InvalidDataException("Duplicate RGB in "+id);
            string display=russian?nameRu:nameEn;
            if(String.IsNullOrWhiteSpace(display) || display.Length>64) throw new InvalidDataException("Invalid display name in "+id);
            colors.Add(new PaletteColor { Id=id, Name=display, R=(byte)r, G=(byte)g, B=(byte)b });
        }
        string hash;
        using(var sha=SHA256.Create()) hash=BitConverter.ToString(sha.ComputeHash(fileBytes)).Replace("-","");
        return new PaletteFile { Colors=colors.ToArray(), Sha256=hash, Path=path };
    }

    private static void PutUInt32(byte[] bytes,int offset,uint value)
    { Buffer.BlockCopy(BitConverter.GetBytes(value),0,bytes,offset,4); }

    private static void PutSingle(byte[] bytes,int offset,float value)
    { Buffer.BlockCopy(BitConverter.GetBytes(value),0,bytes,offset,4); }

    private static int PutString(byte[] bytes,int cursor,string value)
    {
        byte[] encoded=Encoding.Unicode.GetBytes(value+"\0");
        if(cursor<PaletteStringsOffset || cursor+encoded.Length>PaletteStringsEnd)
            throw new InvalidDataException("Player palette strings exceed reserved payload space");
        Buffer.BlockCopy(encoded,0,bytes,cursor,encoded.Length);
        return (cursor+encoded.Length+3)&~3;
    }

    private static void ApplyPalette(byte[] bytes,IntPtr cave,PaletteFile palette)
    {
        PutUInt32(bytes,PaletteCountOffset,(uint)palette.Colors.Length);
        int cursor=PaletteStringsOffset;
        for(int i=0;i<palette.Colors.Length;i++)
        {
            PaletteColor color=palette.Colors[i];
            int idOffset=cursor; cursor=PutString(bytes,cursor,color.Id);
            int nameOffset=cursor; cursor=PutString(bytes,cursor,color.Name);
            int entry=PaletteSourceOffset+i*PaletteEntrySize;
            PutUInt32(bytes,entry,unchecked((uint)cave.ToInt64()+(uint)idOffset));
            PutUInt32(bytes,entry+4,unchecked((uint)cave.ToInt64()+(uint)nameOffset));
            PutSingle(bytes,entry+8,color.R/255.0f);
            PutSingle(bytes,entry+12,color.G/255.0f);
            PutSingle(bytes,entry+16,color.B/255.0f);
        }
    }

    private static byte[] Resource(string name)
    {
        using (Stream s=Assembly.GetExecutingAssembly().GetManifestResourceStream(name))
        {
            if(s==null) throw new InvalidOperationException("Missing embedded "+name);
            using(var m=new MemoryStream()) { s.CopyTo(m); return m.ToArray(); }
        }
    }
    private static void Equal(byte[] a,byte[] b)
    {
        if(a.Length!=b.Length) throw new InvalidOperationException("Payload size mismatch");
        for(int i=0;i<a.Length;i++) if(a[i]!=b[i])
            throw new InvalidOperationException("Lobby hook signature mismatch; nothing further will be installed.");
    }
    private static byte[] Relocate(uint image,uint cave)
    {
        byte[] bytes=Resource("PawLobbyColorsPayload");
        if(bytes.Length!=PayloadSize) throw new InvalidOperationException("Invalid native payload length");
        using(var reader=new BinaryReader(new MemoryStream(Resource("PawLobbyColorsFixups"))))
        {
            uint count=reader.ReadUInt32();
            if(count>4096 || reader.BaseStream.Length!=4+count*12)
                throw new InvalidOperationException("Invalid relocation table");
            var seen=new System.Collections.Generic.HashSet<uint>();
            for(uint i=0;i<count;i++)
            {
                uint kind=reader.ReadUInt32(),offset=reader.ReadUInt32(),value=reader.ReadUInt32();
                if(offset>bytes.Length-4 || !seen.Add(offset))
                    throw new InvalidOperationException("Invalid relocation offset");
                uint result;
                if(kind==1) result=unchecked(image+value);
                else if(kind==2) result=unchecked(cave+value);
                else if(kind==3) result=unchecked(image+value-(cave+offset+4));
                else throw new InvalidOperationException("Invalid relocation type");
                Buffer.BlockCopy(BitConverter.GetBytes(result),0,bytes,(int)offset,4);
            }
        }
        return bytes;
    }
    public static int VerifyOffline()
    {
        PaletteFile palette=LoadPalette();
        if(Expected[MenuSiteIndex].Length!=Encoding.Unicode.GetByteCount("UI/Menus/pcolors.tgi:StagingMenu\0"))
            throw new Exception("Menu path length mismatch");
        Equal(Resource("PawLobbyColorsPayload"),Relocate(0x460000,0x10000000));
        byte[] relocated=Relocate(0x6A0000,0x19000000);
        ApplyPalette(relocated,new IntPtr(0x19000000),palette);
        if(relocated.Length!=PayloadSize) throw new Exception("Relocation failed");
        if(BitConverter.ToInt32(relocated,PaletteCountOffset)!=palette.Colors.Length) throw new Exception("Palette injection failed");
        return 0;
    }

    private static void Write(IntPtr process,IntPtr address,byte[] bytes)
    {
        IntPtr done;
        if(!WriteProcessMemory(process,address,bytes,bytes.Length,out done) || done.ToInt64()!=bytes.Length)
            throw new Win32Exception(Marshal.GetLastWin32Error(),"WriteProcessMemory(lobby colors)");
    }
    private static void Patch(IntPtr process,IntPtr address,byte[] bytes)
    {
        uint old;
        if(!VirtualProtectEx(process,address,bytes.Length,0x40,out old))
            throw new Win32Exception(Marshal.GetLastWin32Error(),"VirtualProtectEx(lobby colors)");
        try { Write(process,address,bytes); }
        finally
        {
            uint ignored;
            if(!VirtualProtectEx(process,address,bytes.Length,old,out ignored))
                throw new Win32Exception(Marshal.GetLastWin32Error(),"Restore protection(lobby colors)");
        }
        if(!FlushInstructionCache(process,address,bytes.Length))
            throw new Win32Exception(Marshal.GetLastWin32Error(),"FlushInstructionCache(lobby colors)");
    }
    public static void Install(IntPtr process,IntPtr image,string logPath)
    {
        VerifyOffline();
        PaletteFile palette=LoadPalette();
        for(int i=0;i<Sites.Length;i++)
        {
            byte[] found=new byte[Expected[i].Length]; IntPtr done;
            if(!ReadProcessMemory(process,Add(image,Sites[i]),found,found.Length,out done) || done.ToInt64()!=found.Length)
                throw new Win32Exception(Marshal.GetLastWin32Error(),"Read lobby hook");
            Equal(found,Expected[i]);
        }
        IntPtr cave=VirtualAllocEx(process,IntPtr.Zero,PayloadSize,0x3000,0x40);
        if(cave==IntPtr.Zero) throw new Win32Exception(Marshal.GetLastWin32Error(),"Allocate lobby payload");
        int attempted=0;
        try
        {
            byte[] bytes=Relocate(unchecked((uint)image.ToInt64()),unchecked((uint)cave.ToInt64()));
            ApplyPalette(bytes,cave,palette);
            // Private palette entropy, completely separate from simulation/map RNG.
            byte[] colorSeed=new byte[4];
            using (var rng=RandomNumberGenerator.Create()) { rng.GetBytes(colorSeed); }
            Buffer.BlockCopy(colorSeed,0,bytes,0x130,4);
            Write(process,cave,bytes);
            if(!FlushInstructionCache(process,cave,bytes.Length))
                throw new Win32Exception(Marshal.GetLastWin32Error(),"Flush payload");
            for(int i=0;i<Sites.Length;i++)
            {
                byte[] branch=new byte[Expected[i].Length];
                for(int j=0;j<branch.Length;j++) branch[j]=0x90;
                branch[0]=Opcodes[i];
                int rel=unchecked((int)(Add(cave,Targets[i]).ToInt64()-Add(image,Sites[i]+5).ToInt64()));
                Buffer.BlockCopy(BitConverter.GetBytes(rel),0,branch,1,4);
                if(i==MenuSiteIndex) branch=Encoding.Unicode.GetBytes("UI/Menus/pcolors.tgi:StagingMenu\0");
                attempted=i+1;
                Patch(process,Add(image,Sites[i]),branch);
            }
            File.AppendAllText(logPath,DateTime.Now.ToString("O")+
                " LOBBY_COLOR_MP r20; completeSessionSnapshot=true; privateColorWireRoundtrip=true; savedColorNameLookup=true; rejoinConflictCheck=true; wireCodec=tagged-uint32-v3; hostDecreeSyncBoundaries=true; rejectInvalidWireIds=true; limitNegativeZeroDisplayFixed=true; menuModVersions=true; customPlayerPalette=true; paletteCount="+palette.Colors.Length+"; paletteSha256="+palette.Sha256+"; stockKingdomPaletteUntouched=true; paletteOrder=saturated_light_dark_neutral; selectAfterRepopulatorEnd=true; expectedStockOrders=334; customOrderIds=334,335; randomOuterLabelTemplateFallback=true; randomOuterLabelDeferredRefresh=true; preserveChoicesAfterMatch=true; lobbyIconRefreshFixed=true; lobbyIconPreview=true; randomIcon=gray; newGameEmptySlotIcon=gray; savedSlotIcon=savedColor; savedLobbyColorsReadOnly=true; savedSourceKind=2; emptySlotPreviewUiOnly=true; randomDefault=true; coloredLabels=true; nativeWorldColorCommit=true; multiplayer=true; hostAuthoritative=true; stableWireIds=true; deterministicMPRandom=true; mpRandomSeed=finalizedWorldSeed; mpRandomShuffle=privateXorshiftFisherYates; nativeRngUntouched=true; allPeersRequirePatch=true; stockSyncChecks=true; cave=0x"+
                cave.ToInt64().ToString("X8")+"; counters=0x"+Add(cave,0x100).ToInt64().ToString("X8")+
                "; hooks=13; customOrders=2; menu=pcolors.tgi; live MP/gameplay/save acceptance pending."+Environment.NewLine);
        }
        catch
        {
            bool reverted=true;
            for(int i=attempted-1;i>=0;i--)
                try { Patch(process,Add(image,Sites[i]),Expected[i]); } catch { reverted=false; }
            // Never free code while a failed rollback might leave a live hook.
            if(reverted) VirtualFreeEx(process,cave,0,0x8000);
            throw;
        }
    }
}
