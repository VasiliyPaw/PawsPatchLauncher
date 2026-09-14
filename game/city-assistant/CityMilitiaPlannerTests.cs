using System;
internal static class CityMilitiaPlannerTests
{
    private static int checks;
    private static void Check(bool ok,string name){if(!ok)throw new Exception(name);checks++;}
    private static CityMilitiaPlanner.City C(uint id,int state=1){return new CityMilitiaPlanner.City{Id=id,State=state};}
    internal static int Main()
    {
        foreach(float firstTime in new[]{0f,.25f,1f})
        {
            var fresh=new CityMilitiaPlanner();var capital=C(80);
            Check(fresh.Update(1,20,true,true,new[]{capital},firstTime)==0,"fresh capital queued even after delayed helper read");
            Check(fresh.Update(1,20,true,true,new[]{capital},firstTime)==0,"paused starting city waits for a simulation tick");
            Check(fresh.Update(1,21,true,true,new[]{capital},firstTime)==80,"starting city opens on first advancing snapshot");
            fresh.Reply(1,21);capital.State=2;
            Check(fresh.Update(1,22,true,true,new[]{capital},firstTime)==0,"starting city open acknowledged");
            capital.State=1;
            Check(fresh.Update(1,23,true,true,new[]{capital},firstTime)==0,"starting city manual close is respected");
            Check(fresh.Update(2,22,true,true,new[]{capital},22)==0,"save restore records the current capital baseline");
            Check(fresh.Update(2,23,true,true,new[]{capital},22)==0,"save restore does not reopen manually closed capital");
        }
        foreach(float firstTime in new[]{float.NaN,float.PositiveInfinity,-1f,1.01f,600f})
        {
            var loaded=new CityMilitiaPlanner();
            loaded.Update(1,600,true,true,new[]{C(81)},firstTime);
            Check(loaded.Update(1,601,true,true,new[]{C(81)},firstTime)==0,"only a known initial world can open existing cities");
        }
        var initialOff=new CityMilitiaPlanner();
        initialOff.Update(1,0,false,true,new[]{C(82)},0);
        Check(initialOff.Update(1,1,true,true,new[]{C(82)},0)==0,"enabling later does not rewrite an existing starting city");
        var pendingCapital=new CityMilitiaPlanner();var unfinished=C(83,0);
        pendingCapital.Update(1,0,true,true,new[]{unfinished},0);
        Check(pendingCapital.Update(1,1,true,true,new[]{unfinished},0)==0,"starting capital waits until militia is available");
        unfinished.State=1;
        Check(pendingCapital.Update(1,2,true,false,new[]{unfinished},0)==0,"starting capital respects settings dialog pause");
        Check(pendingCapital.Update(1,3,true,true,new[]{unfinished},0)==83,"starting capital opens when native command becomes available");
        var p=new CityMilitiaPlanner();var existing=C(1);
        Check(p.Update(1,0,true,true,new[]{existing})==0,"first snapshot baseline");
        Check(p.Update(1,1,true,true,new[]{existing})==0,"existing never rewritten");
        var built=C(2);Check(p.Update(1,2,true,true,new[]{existing,built})==2,"new city opens");
        Check(p.Update(1,3,true,true,new[]{existing,built})==0,"one outstanding command");
        p.Reply(1,3);built.State=2;Check(p.Update(1,4,true,true,new[]{existing,built})==0,"native open confirms");
        built.State=1;Check(p.Update(1,5,true,true,new[]{existing,built})==0,"manual close respected");
        var captured=C(3);Check(p.Update(1,6,true,true,new[]{existing,built,captured})==3,"capture opens");
        p.Reply(3,6);Check(p.Update(1,7,true,true,new[]{existing,built,captured})==0,"already open reply completes");
        Check(p.Update(1,8,true,true,new[]{existing,built})==0,"loss observed");
        Check(p.Update(1,9,true,true,new[]{existing,built,captured})==3,"recapture reopens");
        p.Reply(1,9);Check(p.Update(1,10,true,true,new[]{existing,built})==0,"pending lost city removed");
        captured=C(4,0);Check(p.Update(1,11,true,true,new[]{existing,built,captured})==0,"missing center capability waits");
        captured.State=1;Check(p.Update(1,12,true,true,new[]{existing,built,captured})==4,"fresh center capability used");
        p.Reply(1,12);Check(p.Update(1,23,true,true,new[]{existing,built,captured})==0,"unconfirmed sent command not hammered");
        Check(p.Update(2,0,true,true,new[]{existing,built,captured})==0,"loaded cities form new baseline");
        Check(p.Update(2,1,true,true,new[]{existing,built,captured})==0,"load does not reopen");
        var disabled=C(5);Check(p.Update(2,2,false,true,new[]{existing,built,captured,disabled})==0,"disabled tracks ownership");
        Check(p.Update(2,3,true,true,new[]{existing,built,captured,disabled})==0,"enable does not rewrite existing");
        var paused=C(6);Check(p.Update(2,3,true,true,new[]{existing,paused})==0,"paused world no send");
        Check(p.Update(2,4,true,false,new[]{existing,paused})==0,"dialog pauses dispatch");
        Check(p.Update(2,5,true,true,new[]{existing,paused})==6,"dispatch after pause");
        p.Reply(2,5);Check(p.Update(2,6,true,true,new[]{existing,paused})==0,"rejection backoff");
        Check(p.Update(2,10,true,true,new[]{existing,paused})==6,"bounded retry");
        p.Reply(2,10);Check(p.Update(2,15,true,true,new[]{existing,paused})==6,"last retry");
        p.Reply(2,15);Check(p.Update(2,30,true,true,new[]{existing,paused})==0,"no invalid command loop");
        var late=C(7);Check(p.Update(2,31,true,false,new[]{existing,late})==0,"unissued acquisition queued");
        Check(p.Update(2,32,false,true,new[]{existing,late})==0,"off cancels unissued action");
        Check(p.Update(2,33,true,true,new[]{existing,late})==0,"on does not replay cancelled acquisition");
        Check(p.Update(2,0,true,true,new[]{existing,late})==0,"time rollback resets baseline");
        Console.WriteLine("CITY_MILITIA_PLANNER_PASS "+checks+" checks");return 0;
    }
}
