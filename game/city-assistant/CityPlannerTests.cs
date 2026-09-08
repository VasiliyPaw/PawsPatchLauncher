using System;
using System.Linq;
internal static class CityPlannerTests
{
    private static int checks;
    private static void Check(bool b) { if (!b) throw new Exception("City planner assertion " + (checks + 1)); checks++; }
    private static CityPlanner.Candidate C(uint city, uint data, float cost, params float[] delta)
    { return new CityPlanner.Candidate { City = city, Actor = city + 10, Data = data, Kind = 13, Cost = cost, Delta = delta }; }
    private static CityPlanner.Snapshot S(params CityPlanner.Candidate[] candidates)
    { return new CityPlanner.Snapshot { Epoch=1, Reserve=500, Time=0, Gold=570, Enabled=true, Valid=true, Cities=new uint[]{1,2}, Income=new float[]{10,-4}, Candidates=candidates }; }
    internal static int Main()
    {
        CityPlanner p = new CityPlanner(1);
        CityPlanner.Snapshot s = S(C(1,100,70,20,0),C(1,101,70,0,4),C(2,102,50,0,3));
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=1; s.Gold=569; Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=2; s.Gold=570; var d=p.Update(s); Check(d.Kind==CityPlanner.DecisionKind.Submit && d.Candidate.Data==101);
        for(int i=0;i<20;i++){s.Time+=.1f;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        p.Reply(true,s.Time);s.Busy.Add(1);s.Time+=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time+=1;d=p.Update(s);Check(d.Kind==CityPlanner.DecisionKind.Submit && d.Candidate.City==2);
        p.Reply(false,s.Time);s.Time+=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        // Rejected order is not hammered every refresh.
        s.Time+=5;d=p.Update(s);Check(d.Kind==CityPlanner.DecisionKind.Submit && d.Candidate.City==2);
        p.Reply(true,s.Time);s.Time+=11;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Fault);
        s.Time+=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        // Disable cancels only intentions. Enable recovers a latched safety fault.
        s.Enabled=false;p.Update(s);s.Enabled=true;s.Time+=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        s.Epoch++;s.Time=0;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // An expensive head city waits instead of starving behind cheap cities.
        p=new CityPlanner(2);s=S(C(1,100,100,1,1),C(2,200,1,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);s.Gold=600;s.Time++;
        Check(p.Update(s).Candidate.City==1);
        // Manual work in a city makes the queue move on without replacing it.
        p=new CityPlanner(2);s=S(C(1,100,100,1,1),C(2,200,1,1,1));p.Update(s);s.Time=1;s.Busy.Add(1);
        Check(p.Update(s).Candidate.City==2);
        // Removing a city invalidates its unissued intention.
        p=new CityPlanner(2);s=S(C(1,100,100,1,1),C(2,200,1,1,1));p.Update(s);s.Time=1;p.Update(s);s.Cities=new uint[]{2};s.Time++;
        Check(p.Update(s).Candidate.City==2);
        // No deficit => prefer gold. Empty/invalid input and a paused clock issue nothing.
        p=new CityPlanner(2);s=S(C(1,100,70,2,0),C(1,101,70,8,0));s.Income=new float[]{5,1};p.Update(s);s.Time=1;s.Valid=false;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);s.Valid=true;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=2;Check(p.Update(s).Candidate.Data==101);
        foreach(float bad in new[]{float.NaN,float.PositiveInfinity,float.NegativeInfinity,-1f})
        {p=new CityPlanner(4);s=S(C(1,100,bad,5,5));p.Update(s);s.Time=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        // Fallback selection is stable while waiting for funds.
        p=new CityPlanner(4);s=S(C(1,100,70,0,0),C(1,101,70,0,0));s.Income=new float[]{5,1};s.Gold=0;p.Update(s);
        for(int i=1;i<40;i++){s.Time=i;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        s.Gold=570;s.Time++;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // Switching off during accepted work still observes the acknowledgement.
        p=new CityPlanner(4);s=S(C(1,100,70,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);p.Reply(true,1);
        s.Enabled=false;s.Time=2;s.Busy.Add(1);Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=20;s.Busy.Clear();p.Update(s);s.Enabled=true;s.Time=21;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // Avoid a nominal resource gain that worsens another current deficit more.
        p=new CityPlanner(4);s=S(C(1,100,70,0,4,-10),C(1,101,70,0,2,0));s.Income=new float[]{5,-4,-2};
        p.Update(s);s.Time=1;Check(p.Update(s).Candidate.Data==101);
        // A new deficit overrides a still-legal gold intention waiting for money.
        p=new CityPlanner(4);s=S(C(1,100,70,20,0),C(1,101,70,0,4));s.Gold=0;s.Income=new float[]{5,0};
        p.Update(s);s.Time=1;p.Update(s);s.Income[1]=-4;s.Gold=570;s.Time=2;
        Check(p.Update(s).Candidate.Data==101);
        // Long reserve editing must still observe accepted construction. The
        // snapshot is coherent; Valid is only the UI/new-spending permission.
        p=new CityPlanner(4);s=S(C(1,100,70,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);p.Reply(true,1);
        s.Valid=false;s.Time=2;s.Busy.Add(1);
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Editing);
        s.Time=20;s.Busy.Clear();Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Valid=true;s.Time=21;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        Console.WriteLine("CITY_PLANNER_PASS "+checks+" assertions");return 0;
    }
}
