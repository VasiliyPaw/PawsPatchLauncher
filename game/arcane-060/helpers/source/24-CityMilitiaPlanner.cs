using System;
using System.Collections.Generic;
using System.Linq;

// Each new city center/building is handled once, after construction finishes.
// Completed actors loaded from a save form a baseline; unfinished ones can
// complete later. A player's subsequent manual militia choices are preserved.
internal sealed class CityMilitiaPlanner
{
    internal sealed class City { internal uint Id, CityId; internal int State; internal bool Unfinished, Blocked; } // 0 unavailable, 1 closed, 2 open
    private readonly Dictionary<uint,uint> known = new Dictionary<uint,uint>();
    private readonly Dictionary<uint,int> waiting = new Dictionary<uint,int>();
    private readonly Dictionary<uint,float> retryAt = new Dictionary<uint,float>();
    private bool initialized, awaitingReply;
    private uint epoch, pending;
    private float previousTime=-1, sentAt;
    internal uint Pending { get { return pending; } }
    internal bool PendingOpen { get; private set; }
    internal static City[] ReadSnapshot(byte[] cityRecords,byte[] records)
    {
        if(cityRecords==null || records==null || cityRecords.Length%8!=0 || records.Length%16!=0)return null;
        var owned=new HashSet<uint>();
        for(int i=0;i<cityRecords.Length;i+=8)
        {
            uint id=BitConverter.ToUInt32(cityRecords,i),flags=BitConverter.ToUInt32(cityRecords,i+4);
            // City bit 0 blocks ECONOMIC orders, including during siege.
            // Militia has its own native capability/work-state checks.
            if((flags&2)==0)owned.Add(id);
        }
        var result=new List<City>();var seen=new HashSet<uint>();
        for(int i=0;i<records.Length;i+=16)
        {
            uint city=BitConverter.ToUInt32(records,i),id=BitConverter.ToUInt32(records,i+4);
            uint state=BitConverter.ToUInt32(records,i+8),work=BitConverter.ToUInt32(records,i+12);
            if(!owned.Contains(city) || id==0 || state>2 || work>3)return null;
            if(seen.Add(id))result.Add(new City {Id=id,CityId=city,State=(int)state,
                Unfinished=(work&1)!=0,Blocked=(work&2)!=0});
        }
        return result.ToArray();
    }
    internal uint Update(uint world,float time,bool enabled,bool canIssue,City[] cities,float initialWorldTime=float.NaN)
    {
        bool advances=initialized && epoch==world && time>previousTime;
        if(!initialized || epoch!=world || time<previousTime)
        {
            initialized=true;epoch=world;known.Clear();waiting.Clear();retryAt.Clear();pending=0;awaitingReply=false;
            // The native bridge retains the first observed simulation time, so
            // a slow helper/UI cannot mistake a fresh match for a loaded save.
            // Initial game ticks fit in the first second; later saves are not
            // replayed, and toggling the preference never rewrites known cities.
            bool starting=initialWorldTime>=0 && initialWorldTime<=1;
            foreach(var city in cities)
            {
                known[city.Id]=city.CityId;
                if((starting || city.Unfinished) && (city.Unfinished || city.State!=(enabled?2:1)))waiting[city.Id]=0;
            }
            previousTime=time;return 0;
        }
        previousTime=time;
        var owned=new HashSet<uint>(cities.Select(c=>c.Id));
        foreach(uint id in known.Keys.Where(id=>!owned.Contains(id)).ToArray())known.Remove(id);
        foreach(uint id in waiting.Keys.Where(id=>!owned.Contains(id)).ToArray()){waiting.Remove(id);retryAt.Remove(id);}
        foreach(var city in cities)
        {
            uint previousCity;
            if(!known.TryGetValue(city.Id,out previousCity) || previousCity!=city.CityId)
            {known[city.Id]=city.CityId;waiting[city.Id]=0;retryAt.Remove(city.Id);}
            if(city.Id!=pending && !city.Unfinished && city.State==(enabled?2:1))
            {waiting.Remove(city.Id);retryAt.Remove(city.Id);}
        }
        if(pending!=0 && (!owned.Contains(pending) || (!awaitingReply && cities.Any(c=>c.Id==pending && !c.Unfinished && c.State==(PendingOpen?2:1)))))
        {waiting.Remove(pending);pending=0;awaitingReply=false;}
        if(pending!=0)
        {
            // Never keep reopening after an unconfirmed sent order: a player's
            // intervening militia command wins. No repeated command flood.
            if(!awaitingReply && time-sentAt>=10){waiting.Remove(pending);pending=0;}
            else return 0;
        }
        if(!advances || !canIssue)return 0;
        foreach(var city in cities)
        {
            float retry;
            if(city.Unfinished || city.Blocked || city.State!=(enabled?1:2) || !waiting.ContainsKey(city.Id) ||
                (retryAt.TryGetValue(city.Id,out retry) && time<retry))continue;
            pending=city.Id;PendingOpen=enabled;awaitingReply=true;sentAt=time;return pending;
        }
        return 0;
    }
    internal void Reply(uint result,float time)
    {
        if(pending==0 || !awaitingReply)return;
        awaitingReply=false;sentAt=time;
        if(result==1)return;
        // A native disabling state or construction can change between observation
        // and dispatch. Keep the acquisition pending without consuming a retry;
        // only an unsent order is retried, after another fresh snapshot.
        if(result==4){retryAt[pending]=time+5;pending=0;return;}
        int attempts;
        if(result==3 || !waiting.TryGetValue(pending,out attempts) || attempts>=2)waiting.Remove(pending);
        else{waiting[pending]=attempts+1;retryAt[pending]=time+5;}
        pending=0;
    }
}
