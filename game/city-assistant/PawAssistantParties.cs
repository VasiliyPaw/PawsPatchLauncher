using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

internal static partial class PawAssistantRuntime
{
    private static CityPartyStore partyStore;
    private static string partyGameRoot,partyId,lastPartySettings,lastPartyError;
    private static uint partyGeneration,partySaveSerial;
    private static readonly Dictionary<uint,string> partyIds=new Dictionary<uint,string>();
    private sealed class SavedParty {internal string Id,Filename;internal DateTime Deadline;}
    private static readonly List<SavedParty> pendingSaves=new List<SavedParty>();

    private static string NativeFilename(byte[] data,int start,int length)
    {return Encoding.Unicode.GetString(data,start,length).Split('\0')[0];}
    private static string ResolvePartySave(string filename)
    {
        if(string.IsNullOrWhiteSpace(filename) || filename.Length>511)return null;
        filename=filename.Replace('/',Path.DirectorySeparatorChar);
        // Virtual resource paths may omit the extension or include data/Save.
        if(!Path.HasExtension(filename))filename+=".RSG";
        if(!string.Equals(Path.GetExtension(filename),".rsg",StringComparison.OrdinalIgnoreCase))return null;
        string documents=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"Kohan2");
        var roots=new[]{Path.Combine(documents,"data","Save"),Path.Combine(partyGameRoot,"data","Save")};
        var candidates=new List<string>();
        if(Path.IsPathRooted(filename))candidates.Add(filename);
        else
        {
            candidates.Add(Path.Combine(documents,filename));candidates.Add(Path.Combine(documents,"data",filename));
            candidates.Add(Path.Combine(roots[0],filename));candidates.Add(Path.Combine(partyGameRoot,filename));
            candidates.Add(Path.Combine(partyGameRoot,"data",filename));candidates.Add(Path.Combine(roots[1],filename));
        }
        foreach(string candidate in candidates)
        {
            string full=Path.GetFullPath(candidate);
            foreach(string root in roots)
                if(full.StartsWith(Path.GetFullPath(root)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase) && File.Exists(full))return full;
        }
        return null;
    }
    private static void ReadSuccessfulPartySaves()
    {
        uint latest=Pointer(state+0x1c0);
        if(unchecked(latest-partySaveSerial)>16)
        {logger("ASSISTANT party save notification overflow; skipped old bindings");partySaveSerial=latest-16;}
        while(partySaveSerial!=latest)
        {
            uint serial=partySaveSerial+1,address=state+0x41000+(serial&15)*0x500;
            byte[] data=memory.Read(address,0x430);
            if(BitConverter.ToUInt32(data,0)!=serial || Pointer(address)!=serial)break;
            string id;
            if(partyIds.TryGetValue(BitConverter.ToUInt32(data,4),out id))
            {
                string filename=NativeFilename(data,16,1024);
                var settings=new CityPartySettings {Enabled=BitConverter.ToUInt32(data,0x410)==1,Reserve=BitConverter.ToUInt32(data,0x414)};
                for(int i=1;i<5;i++)settings.Floors[i]=BitConverter.ToSingle(data,0x414+i*4);
                settings=CityPartySettings.Decode(settings.Encode());
                partyStore.Write(id,settings);
                if(id==partyId)lastPartySettings=settings.Encode();
                if(filename.Length>0)pendingSaves.Add(new SavedParty {Id=id,Filename=filename,Deadline=DateTime.UtcNow.AddSeconds(30)});
            }
            partySaveSerial=serial;
        }
        for(int i=pendingSaves.Count-1;i>=0;i--)
        {
            var saved=pendingSaves[i];
            try
            {
                string path=ResolvePartySave(saved.Filename);
                if(path==null)throw new IOException("Saved file is not yet available.");
                partyStore.Bind(saved.Id,path);pendingSaves.RemoveAt(i);
                logger("ASSISTANT party save bound="+Path.GetFileName(path)+" party="+saved.Id);
            }
            catch(IOException)
            {
                if(DateTime.UtcNow>saved.Deadline)
                {pendingSaves.RemoveAt(i);logger("ASSISTANT party save binding timed out="+saved.Filename);}
            }
        }
    }
    private static bool UpdatePartyPreferences()
    {
        try
        {
            ReadSuccessfulPartySaves();
            uint generation=Pointer(state+0x1b0);
            if(generation==0 || (generation&1)!=0 || Pointer(state+0x74)==0)return false;
            if(generation==partyGeneration && Pointer(state+0xb8)==1)return true;
            uint kind=Pointer(state+0x1b8);
            string source=NativeFilename(memory.Read(state+0x1f000,1024),0,1024);
            if(Pointer(state+0x1b0)!=generation)return false;
            string save=null;
            if(kind==2)
            {
                save=ResolvePartySave(source);
                if(save==null)throw new IOException("Cannot resolve selected save: "+source);
            }
            else if(kind>5)throw new IOException("Session source is not ready.");
            string id;
            if(!partyIds.TryGetValue(generation,out id))
            {id=partyStore.Open(save);partyIds[generation]=id;}
            var settings=partyStore.Read(id);
            // File I/O has finished. Freeze only for a short, coherent update
            // of our private payload; never write to game simulation objects.
            memory.Suspend();
            try
            {
                if(Pointer(state+0x1b0)!=generation || Pointer(state+0x74)==0)return false;
                policy=new CityPolicy {NewCitiesOpenMilitia=policy.NewCitiesOpenMilitia,Floors=(float[])settings.Floors.Clone()};
                floorRevision=Pointer(state+0x1c020)+2;
                memory.Write(state+0x1c020,BitConverter.GetBytes(floorRevision));
                byte[] floors=new byte[20];for(int i=1;i<5;i++)Array.Copy(BitConverter.GetBytes(settings.Floors[i]),0,floors,i*4,4);
                memory.Write(state+0x1b000,floors);memory.Write(state+0x1c024,BitConverter.GetBytes(floorRevision));
                memory.Write(state+0x40,BitConverter.GetBytes(settings.Enabled?1:0));
                memory.Write(state+0x44,BitConverter.GetBytes(settings.Reserve));
                memory.Write(state+0x7c,BitConverter.GetBytes(1));
                memory.Write(state+0x54,BitConverter.GetBytes(Pointer(state+0x54)+1));
                memory.Write(state+0x70,BitConverter.GetBytes(Environment.TickCount));
                memory.Write(state+0x1b4,BitConverter.GetBytes(generation));
                memory.Write(state+0xb8,BitConverter.GetBytes(1));
                partyGeneration=generation;partyId=id;lastPartySettings=settings.Encode();lastPartyError=null;
            }
            finally {memory.Resume();}
            logger("ASSISTANT party restored="+id+" source="+(save==null?"new match":Path.GetFileName(save))+
                " enabled="+settings.Enabled+" reserve="+settings.Reserve);
            return true;
        }
        catch(Exception ex)
        {
            if(ex.Message!=lastPartyError){logger("ASSISTANT party preferences: "+ex.Message);lastPartyError=ex.Message;}
            PublishStatus(CityAdvice(2),CityAdvice(3));
            return false;
        }
    }
    private static void SavePartyPreferences(byte[] ui)
    {
        if(partyId==null || !floorsReady || partyGeneration!=Pointer(state+0x1b0) || Pointer(state+0xb8)!=1)return;
        uint revision=BitConverter.ToUInt32(ui,0x14);
        var settings=new CityPartySettings {Enabled=BitConverter.ToUInt32(ui,0)==1,Reserve=BitConverter.ToUInt32(ui,4),Floors=(float[])policy.Floors.Clone()};
        if(revision!=Pointer(state+0x54) || Pointer(state+0x1c020)!=floorRevision)return;
        string text=settings.Encode();if(text==lastPartySettings)return;
        try {partyStore.Write(partyId,CityPartySettings.Decode(text));lastPartySettings=text;logger("ASSISTANT party preferences saved="+partyId);}
        catch(Exception ex){if(ex.Message!=lastPartyError){logger("ASSISTANT party preferences save: "+ex.Message);lastPartyError=ex.Message;}}
    }
}
