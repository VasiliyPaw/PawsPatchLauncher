using System;
using System.Collections.Generic;
using System.Linq;

// Observes ownership, never militia memory. One ordinary native command is sent
// for a newly acquired city. A new world's initial cities are eligible too;
// cities restored from an established saved match form a baseline.
internal sealed class CityMilitiaPlanner
{
    internal sealed class City { internal uint Id; internal int State; } // 0 unavailable, 1 closed, 2 open
    private readonly HashSet<uint> known = new HashSet<uint>();
    private readonly Dictionary<uint,int> waiting = new Dictionary<uint,int>();
    private readonly Dictionary<uint,float> retryAt = new Dictionary<uint,float>();
    private bool initialized, awaitingReply;
    private uint epoch, pending;
    private float previousTime=-1, sentAt;
    internal uint Pending { get { return pending; } }
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
                known.Add(city.Id);
                if(starting && enabled && city.State!=2)waiting[city.Id]=0;
            }
            previousTime=time;return 0;
        }
        previousTime=time;
        var owned=new HashSet<uint>(cities.Select(c=>c.Id));
        foreach(uint id in known.Where(id=>!owned.Contains(id)).ToArray())known.Remove(id);
        foreach(uint id in waiting.Keys.Where(id=>!owned.Contains(id)).ToArray()){waiting.Remove(id);retryAt.Remove(id);}
        foreach(var city in cities)
        {
            if(known.Add(city.Id) && enabled && city.State!=2)waiting[city.Id]=0;
            if(city.State==2)waiting.Remove(city.Id);
        }
        if(pending!=0 && (!owned.Contains(pending) || cities.Any(c=>c.Id==pending && c.State==2)))
        {waiting.Remove(pending);pending=0;awaitingReply=false;}
        if(!enabled){waiting.Clear();retryAt.Clear();return 0;}
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
            if(city.State!=1 || !waiting.ContainsKey(city.Id) ||
                (retryAt.TryGetValue(city.Id,out retry) && time<retry))continue;
            pending=city.Id;awaitingReply=true;sentAt=time;return pending;
        }
        return 0;
    }
    internal void Reply(uint result,float time)
    {
        if(pending==0 || !awaitingReply)return;
        awaitingReply=false;sentAt=time;
        if(result==1)return;
        int attempts;
        if(result==3 || !waiting.TryGetValue(pending,out attempts) || attempts>=2)waiting.Remove(pending);
        else{waiting[pending]=attempts+1;retryAt[pending]=time+5;}
        pending=0;
    }
}
