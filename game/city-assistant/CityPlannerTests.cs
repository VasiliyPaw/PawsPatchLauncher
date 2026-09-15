using System;
using System.Linq;
internal static class CityPlannerTests
{
    private static int checks;
    private static void Check(bool b) { if (!b) throw new Exception("City planner assertion " + (checks + 1)); checks++; }
    private static CityPlanner.Candidate C(uint city, uint data, float cost, params float[] delta)
    { return new CityPlanner.Candidate { City = city, Actor = city + 10, Data = data, Kind = 13, Cost = cost, Delta = delta }; }
    private static CityPlanner.Snapshot S(params CityPlanner.Candidate[] candidates)
    { return new CityPlanner.Snapshot { Epoch=1, Reserve=500, Time=0, Gold=570, Enabled=true, Valid=true, Cities=new uint[]{1,2}, Income=new float[]{10,-4}, ShortageCost=new float[]{0,2,3,4,5}, Candidates=candidates }; }
    internal static int Main()
    {
        CityPlanner p = new CityPlanner(1);
        CityPlanner.Snapshot s = S(C(1,100,70,4,0),C(1,101,70,0,4),C(2,102,50,0,3));
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=1; s.Gold=499; Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=2; s.Gold=570; var d=p.Update(s); Check(d.Kind==CityPlanner.DecisionKind.Submit && d.Candidate.Data==101);
        for(int i=0;i<20;i++){s.Time+=.1f;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        p.Reply(true,s.Time);s.Busy.Add(1);s.Construction=new[]{d.Candidate};s.Time+=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
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
        // Affordable native work can proceed while another city waits for money.
        p=new CityPlanner(2);s=S(C(1,100,100,1,1),C(2,200,1,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Candidate.City==2);p.Reply(false,s.Time);s.Gold=600;s.Time++;
        Check(p.Update(s).Candidate.City==1);
        // Manual work in a city makes the queue move on without replacing it.
        p=new CityPlanner(2);s=S(C(1,100,100,1,1),C(2,200,1,1,1));p.Update(s);s.Time=1;s.Busy.Add(1);
        Check(p.Update(s).Candidate.City==2);
        // Removing a city invalidates its unissued intention.
        p=new CityPlanner(2);s=S(C(1,100,100,1,1),C(2,200,1,1,1));s.Gold=0;p.Update(s);s.Time=1;p.Update(s);s.Cities=new uint[]{2};s.Gold=570;s.Time++;
        Check(p.Update(s).Candidate.City==2);
        // No deficit => prefer gold. Empty/invalid input and a paused clock issue nothing.
        p=new CityPlanner(2);s=S(C(1,100,70,2,0),C(1,101,70,8,0));s.Income=new float[]{5,1};p.Update(s);s.Time=1;s.Valid=false;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);s.Valid=true;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=2;Check(p.Update(s).Candidate.Data==101);
        foreach(float bad in new[]{float.NaN,float.PositiveInfinity,float.NegativeInfinity,-1f})
        {p=new CityPlanner(4);s=S(C(1,100,bad,5,5));p.Update(s);s.Time=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        // Fallback selection is stable while waiting for funds.
        p=new CityPlanner(4);s=S(C(1,100,70,0,0),C(1,101,70,0,0));s.Income=new float[]{5,1};s.Gold=0;p.Update(s);
        foreach(var c in s.Candidates){c.Kind=21;c.Family="barracks";c.Target="advanced";}
        for(int i=1;i<40;i++){s.Time=i;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        s.Gold=570;s.Time++;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // Switching off during accepted work still observes the acknowledgement.
        p=new CityPlanner(4);s=S(C(1,100,70,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);p.Reply(true,1);
        s.Enabled=false;s.Time=2;s.Busy.Add(1);s.Construction=s.Candidates;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=20;s.Busy.Clear();s.Construction=new CityPlanner.Candidate[0];p.Update(s);s.Enabled=true;s.Time=21;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // Avoid a nominal resource gain that worsens another current deficit more.
        p=new CityPlanner(4);s=S(C(1,100,70,0,4,-10),C(1,101,70,0,2,0));s.Income=new float[]{5,-4,-2};
        p.Update(s);s.Time=1;Check(p.Update(s).Candidate.Data==101);
        // Resource targets outrank ordinary gold when no market can compete.
        p=new CityPlanner(4);s=S(C(1,100,70,20,0),C(1,101,70,0,4));s.Gold=0;s.Income=new float[]{5,0};
        p.Update(s);s.Time=1;p.Update(s);s.Income[1]=-4;s.Gold=570;s.Time=2;
        Check(p.Update(s).Candidate.Data==101); // ordinary +20 gold must wait for resources.
        // Long reserve editing must still observe accepted construction. The
        // snapshot is coherent; Valid is only the UI/new-spending permission.
        p=new CityPlanner(4);s=S(C(1,100,70,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);p.Reply(true,1);
        s.Valid=false;s.Time=2;s.Busy.Add(1);s.Construction=s.Candidates;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Editing);
        s.Time=20;s.Busy.Clear();s.Construction=new CityPlanner.Candidate[0];Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Valid=true;s.Time=21;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // Every economic resource is protected, including an existing gold deficit.
        for(int resource=0;resource<5;resource++)
        foreach(float before in new[]{-10f,-1f,0f,1f})
        {
            float[] income=Enumerable.Repeat(10f,5).ToArray();income[resource]=before;
            float[] delta=new float[5];delta[resource]=-2;delta[(resource+1)%5]=100;
            var candidate=C(1,100,0,delta);
            Check(!CityPlanner.Protects(candidate,income,income,new CityPolicy()));
        }
        // Spending exactly down to the floor is permitted, crossing it is not.
        var policy=new CityPolicy();policy.Floors[3]=2;
        Check(CityPlanner.Protects(C(1,100,0,0,0,0,-3,0),new float[]{10,0,0,5,0},new float[]{10,0,0,5,0},policy));
        Check(!CityPlanner.Protects(C(1,100,0,0,0,0,-4,0),new float[]{10,0,0,5,0},new float[]{10,0,0,5,0},policy));
        // Outstanding adverse commitments are protected; future gains do not count.
        Check(!CityPlanner.Protects(C(1,100,0,5,-3),new float[]{5,5},new float[]{5,1},new CityPolicy()));
        // Resource targets apply globally across cities, ahead of non-market gold.
        p=new CityPlanner(1);s=S(C(1,100,0,100,0),C(2,200,0,0,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Candidate.City==2);
        // Gold-producing branch that deepens the iron shortage must never win.
        p=new CityPlanner(1);s=S(C(1,100,0,50,-1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Protected);
        // Positive resource targets also precede ordinary gold, before a deficit starts.
        p=new CityPlanner(1);s=S(C(1,100,0,100,0),C(2,200,0,0,1));s.Income[1]=0;s.Policy.Floors[1]=2;p.Update(s);s.Time=1;
        Check(p.Update(s).Candidate.City==2);
        // User's branch rule is exact, and city overrides inherit otherwise.
        var branch=C(1,100,0,0,1);branch.Kind=21;branch.Family="forge";branch.Target="iron";branch.BranchCount=2;
        policy=new CityPolicy();policy.Branches["forge"]="manual";Check(!policy.Allows(branch));
        branch.BranchCount=1;Check(policy.Allows(branch));policy.Branches["forge"]="gold";Check(!policy.Allows(branch));
        policy.CityBranches[1]=new System.Collections.Generic.Dictionary<string,string>{{"forge","iron"}};Check(policy.Allows(branch));
        policy.Excluded.Add(1);Check(!policy.Allows(branch));policy.ClearCities();Check(!policy.Allows(branch));
        policy.Branches["forge"]="auto";policy.AllowUpgrade=false;Check(!policy.Allows(branch));
        policy.AllowUpgrade=true;policy.AllowNew=false;Check(policy.Allows(branch));branch.Kind=13;Check(!policy.Allows(branch));
        // Unknown manual work must settle before another automatic resource commitment.
        p=new CityPlanner(1);s=S(C(1,100,0,10,1));p.Update(s);s.Time=1;s.UnknownConstruction=true;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Construction);
        s.UnknownConstruction=false;s.Time=2;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // A fresh process moves both definitions and strings. Rules must still
        // match their internal names, independently of translated display text.
        string familyA=CityPolicy.DefinitionKey(0x10000,a=>a==0x10008?0x20000u:0u,a=>a==0x20000?"human_blacksmith":"");
        string familyB=CityPolicy.DefinitionKey(0x30000,a=>a==0x30008?0x40000u:0u,a=>a==0x40000?"human_blacksmith":"");
        string targetA=CityPolicy.DefinitionKey(0x50000,a=>a==0x50008?0x60000u:0u,a=>a==0x60000?"human_foundry":"");
        string targetB=CityPolicy.DefinitionKey(0x70000,a=>a==0x70008?0x80000u:0u,a=>a==0x80000?"human_foundry":"");
        Check(familyA==familyB && familyA=="def:human_blacksmith");Check(targetA==targetB);
        policy=new CityPolicy();policy.Branches[familyA]=targetA;
        string prefs=System.IO.Path.Combine(System.IO.Path.GetTempPath(),"paw-policy-test-"+Guid.NewGuid().ToString("N"),"policy.ini");
        try
        {
            policy.Save(prefs);policy=CityPolicy.Load(prefs);
            branch.Kind=21;branch.Family=familyB;branch.Target=targetB;branch.Name="Кузнечный цех";
            Check(policy.Allows(branch));branch.Name="Ironworks";Check(policy.Allows(branch));
            branch.Target="def:human_iron_market";Check(!policy.Allows(branch));
            branch.Target="unavailable";Check(!policy.Allows(branch));
            branch.Family="unavailable";Check(!policy.Allows(branch));
        }
        finally { if(System.IO.File.Exists(prefs))System.IO.File.Delete(prefs);System.IO.Directory.Delete(System.IO.Path.GetDirectoryName(prefs)); }
        bool rejected=false;try {CityPolicy.DefinitionKey(0x10000,a=>0x20000,a=>"");}catch(System.IO.InvalidDataException){rejected=true;}Check(rejected);
        Check(new CityPolicy().NewCitiesOpenMilitia);
        EconomyRegressions();
        ParallelRegressions();
        DevelopmentRegressions();
        NetIncomeRegressions();
        ResourcePriorityRegressions();
        SavingPriorityRegressions();
        Console.WriteLine("CITY_PLANNER_PASS "+checks+" assertions");return 0;
    }
    private static CityPlanner.Candidate Upgrade(uint city,uint actor,uint data,params float[] delta)
    { var c=C(city,data,50,delta);c.Actor=actor;c.Kind=21;c.Family="def:human_blacksmith";c.Target="def:test";return c; }
    private static CityPlanner.Decision Choose(CityPlanner.Snapshot s)
    {var planner=new CityPlanner(1);s.Time=0;s.Gold=10000;planner.Update(s);s.Time=1;return planner.Update(s);}
    private static void ParallelRegressions()
    {
        // Siege of one city neither blocks other cities nor acknowledges an order.
        var s=S(C(1,100,70,20,0),C(2,200,70,20,0));s.Income=new float[]{10,0};
        s.Busy.Add(1);Check(Choose(s).Candidate.City==2);
        var p=new CityPlanner(1);s.Busy.Clear();s.Time=0;p.Update(s);s.Time=1;
        var first=p.Update(s);Check(first.Kind==CityPlanner.DecisionKind.Submit);
        p.Reply(true,s.Time);s.Busy.Add(1);s.Time=2;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Pending);
        // An unrelated manual construction cannot masquerade as our paid order.
        s.Construction=new[]{C(1,999,70,20,0)};s.Time=3;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Construction=new[]{C(1,100,70,20,0)};s.Construction[0].Actor=800;
        s.Gold=570;s.Time=4;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Time=5;Check(p.Update(s).Candidate.City==2); // first city is STILL building
        // Money is re-read after acknowledgement; a completed debit cannot be
        // spent again, and the configured gold reserve is preserved.
        p=new CityPlanner(1);s=S(C(1,100,70,20,0),C(2,200,70,20,0));s.Income=new float[]{10,0};
        p.Update(s);s.Time=1;first=p.Update(s);p.Reply(true,1);
        s.Gold=500;s.Busy.Add(1);s.Construction=new[]{first.Candidate};s.Time=2;p.Update(s);
        s.Time=3;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Gold);
        s.Gold=570;s.Time=4;Check(p.Update(s).Candidate.City==2);
        for(int r=1;r<5;r++)
        {
            float[] income=new float[]{30,10,10,10,10};income[r]=-3;
            float[] effect=new float[5];effect[0]=20;effect[r]=0;
            s=S(Upgrade(2,22,200,effect));s.Income=income;s.Policy.Floors[r]=2;
            // No way to fix the shortage: safe gold remains useful.
            Check(Choose(s).Candidate.Data==200);
            effect[r]=-1;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
            effect[r]=0;effect[(r%4)+1]=-11;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
            effect[(r%4)+1]=0;
            float[] relief=new float[5];relief[r]=6;
            s.Candidates=new[]{s.Candidates[0],Upgrade(1,11,101,relief)};
            Check(Choose(s).Candidate.Data==101); // non-market gold cannot displace target resources.
            s.Busy.Add(1);Check(Choose(s).Candidate.Data==200);
            s.Busy.Clear();s.Policy.Excluded.Add(1);Check(Choose(s).Candidate.Data==200);
            // Ongoing work already covers target: don't build duplicate relief.
            s.Policy.Excluded.Clear();s.GoalIncome=(float[])income.Clone();s.GoalIncome[r]=3;
            Check(Choose(s).Candidate.Data==200);
            // ...but its future positive income cannot finance a gold fork yet.
            effect[r]=-1;Check(Choose(s).Candidate.Data==101); // safe surplus building; unsafe gold still excluded
            effect[r]=0;s.GoalIncome=null;
            s.Forecast=(float[])income.Clone();s.Forecast[(r%4)+1]=0;
            effect[(r%4)+1]=-1;Check(Choose(s).Candidate.Data==101);
        }
        // Exact upgrade actor (not only city+target); native new-build actor differs.
        var u=Upgrade(1,11,100,20,0);p=new CityPlanner(1);s=S(u);s.Income=new float[]{10,0};
        p.Update(s);s.Time=1;p.Update(s);p.Reply(true,1);s.Busy.Add(1);
        s.Construction=new[]{Upgrade(1,12,100,20,0)};s.Time=2;p.Update(s);
        Check(p.Status==CityPlanner.StatusKind.Pending);
        s.Construction=new[]{u};s.Time=3;p.Update(s);Check(p.Status!=CityPlanner.StatusKind.Pending);
        // Expected gains prevent redundant gold preparation, too.
        var provider=Upgrade(1,11,100,0,4);var market=Upgrade(2,22,200,40,-3);
        s=S(provider,market);s.Income=new float[]{20,0};s.GoalIncome=new float[]{20,4};
        Check(Choose(s).Candidate==provider); // no further economy goal: safe random development
        s.GoalIncome=null;Check(Choose(s).Candidate==provider);
        // Cancel/completion is reflected by each fresh snapshot, without a stale
        // persistent resource reservation; load/epoch drops old pending orders.
        s.GoalIncome=new float[]{20,float.NaN};Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        s.GoalIncome=null;s.Income[1]=4;Check(Choose(s).Candidate==market);
        p=new CityPlanner(1);s=S(C(1,100,70,20,0));p.Update(s);s.Time=1;p.Update(s);p.Reply(true,1);
        s.Epoch++;s.Time=0;p.Update(s);s.Time=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
    }
    private static void EconomyRegressions()
    {
        foreach(int nativeCount in new[]{9,10})
        {
            byte[] native=new byte[4*nativeCount];
            for(int i=0;i<nativeCount;i++)Array.Copy(BitConverter.GetBytes(1000f+i),0,native,i*4,4);
            for(int i=0;i<5;i++)Array.Copy(BitConverter.GetBytes(10f+i),0,native,CityResourceOrder.NativeIndex(i,nativeCount)*4,4);
            Check(CityResourceOrder.Read(native,0,nativeCount).SequenceEqual(new[]{10f,11f,12f,13f,14f}));
            for(int i=1;i<5;i++)
            {
                var income=CityResourceOrder.Read(native,0,nativeCount);
                byte[] nativeDelta=new byte[4*nativeCount];
                Array.Copy(BitConverter.GetBytes(-2f),0,nativeDelta,CityResourceOrder.NativeIndex(i,nativeCount)*4,4);
                var policy=new CityPolicy();policy.Floors[i]=income[i]-1;
                Check(!CityPlanner.Protects(C(1,100,0,CityResourceOrder.Read(nativeDelta,0,nativeCount)),income,income,policy));
            }
        }
        foreach(int count in new[]{0,5,8,11,16})Check(!CityResourceOrder.Supported(count));
        // General property, not special-cased numbers: every non-gold resource,
        // arbitrary floors, fractional income, and both construction/order kinds.
        for(int r=1;r<5;r++)
        foreach(float target in new[]{0f,2f,5f,17f,50f})
        foreach(float before in new[]{-3f,0f,2f,6f,10f,104f,278f})
        foreach(float delta in new[]{-300f,-6f,-4f,-2.5f,0f,3f})
        {
            var income=Enumerable.Repeat(500f,5).ToArray();income[r]=before;
            var effects=new float[5];effects[r]=delta;
            var policy=new CityPolicy();policy.Floors[r]=target;
            Check(CityPlanner.Protects(C(1,100,0,effects),income,income,policy)==(delta>=0 || before+delta>=Math.Min(before,target)));
        }
        var gold=Upgrade(1,11,100,20,0,0,-2,0);
        var more=Upgrade(1,11,101,0,0,0,6,0);
        var s=S(gold,more);s.Income=new float[]{30,10,10,6,60};s.Policy.Floors[3]=2;
        Check(Choose(s).Candidate==gold);
        s.Policy.Floors[3]=12;Check(Choose(s).Candidate==more);
        s.Policy.Floors[3]=0;s.Income=new float[]{400,278,150,104,104};s.Policy.Floors[4]=50;
        s.Candidates=new[]{more};Check(Choose(s).Candidate==more); // always-on idle fallback
        // Every race's profitable market can deepen resource deficits, both
        // as new construction and as a market upgrade. Gold remains protected.
        foreach(string race in new[]{"human","drauga","gauri","haroun","shadow","undead"})
        for(int r=1;r<5;r++)
        foreach(uint kind in new uint[]{13,21})
        {
            var market=Upgrade(1,11,100,40,-9,-9,-9,-9);market.Kind=kind;
            market.Family=kind==21?"def:"+race+"_market":"def:"+race+"_settlement";
            market.Target=kind==13?"def:"+race+"_market":"def:"+race+"_bazaar";
            var income=new float[]{100,6,6,6,6};var policy=new CityPolicy();policy.Floors=new float[]{0,5,5,5,5};
            Check(CityPlanner.Protects(market,income,income,policy));
            var committed=(float[])income.Clone();committed[r]=5;
            Check(CityPlanner.Protects(market,income,committed,policy));
            income[r]=5;Check(CityPlanner.Protects(market,income,income,policy));
            income[r]=-4;Check(CityPlanner.Protects(market,income,income,policy));
            committed[r]=-100;Check(CityPlanner.Protects(market,income,committed,policy));
            market.Delta[0]=0;Check(!CityPlanner.Protects(market,income,committed,policy));
            income[r]=6;market.Delta[0]=-101;Check(!CityPlanner.Protects(market,income,income,policy));
        }
        // All native mine types use the same resource/gold/random priorities.
        foreach(string race in new[]{"human","drauga","gauri","haroun","shadow","undead"})
        foreach(string resource in new[]{"stone","wood","iron","mana","gold"})
        {
            int r=Array.IndexOf(new[]{"gold","stone","wood","iron","mana"},resource);
            var mine=Upgrade(1,11,100,0,0,0,0,0);mine.IsMine=true;mine.Family="def:"+race+"_mine_"+resource;
            mine.Target=mine.Family+"_upgrade";mine.Delta[r]=6;
            s=S(mine);s.Income=new float[]{30,10,10,10,10};s.Income[r]=r==0?30:-3;
            Check(Choose(s).Candidate==mine);
            s.Income=new float[]{30,10,10,10,10};mine.Delta=new float[5];Check(Choose(s).Candidate==mine);
            s.Income[1]=0;Check(Choose(s).Candidate==mine); // unreachable target does not freeze safe fallback
        }
        // Goal forecast sees manually queued positive gains. Real available
        // income/cash still governs eligibility; cancellation removes forecasts.
        var stone=Upgrade(1,11,101,0,8,0,0,0);var iron=Upgrade(1,12,102,0,0,0,8,0);
        s=S(stone,iron);s.Income=new float[]{30,-3,10,-3,10};s.GoalIncome=new float[]{30,5,10,-3,10};
        s.Construction=new[]{Upgrade(1,13,999,0,8,0,0,0)};
        Check(Choose(s).Candidate==iron);
        s.GoalIncome=new float[]{30,5,10,5,10};Check(Choose(s).Kind==CityPlanner.DecisionKind.Submit); // surplus random development
        s.GoalIncome=null;s.Construction=new CityPlanner.Candidate[0];Check(Choose(s).Kind==CityPlanner.DecisionKind.Submit);
        // Same city, distinct actors can join an existing queue. Mutually
        // exclusive upgrades on its pending actor and duplicate builds cannot.
        var p=new CityPlanner(1);s=S(stone,iron);s.Income=new float[]{30,-3,10,-3,10};s.Gold=1000;
        p.Update(s);s.Time=1;var first=p.Update(s);p.Reply(true,1);s.Construction=new[]{first.Candidate};s.Gold-=first.Candidate.Cost;
        s.Time=2;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);s.Time=3;
        var second=p.Update(s);Check(second.Kind==CityPlanner.DecisionKind.Submit && second.Candidate.City==first.Candidate.City && second.Candidate.Actor!=first.Candidate.Actor);
        var otherBranch=Upgrade(1,11,103,0,12,0,0,0);s=S(stone,otherBranch);s.Construction=new[]{stone};
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        var build=C(1,100,5,20,0);s=S(build);s.Construction=new[]{C(1,100,5,20,0)};s.Construction[0].Actor=999;
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        // Removed gold target must not remain active from old preferences.
        var old=new CityPolicy();old.Floors[0]=1000;Check(old.Floor(0)==0);
        Check(CityPlanner.Protects(C(1,100,0,-1,0,0,0,3),new float[]{30,0,0,0,0},new float[]{30,0,0,0,0},old));
        string prefs=System.IO.Path.Combine(System.IO.Path.GetTempPath(),"paw-policy-test-"+Guid.NewGuid().ToString("N"),"policy.ini");
        try
        {
            Check(CityPolicy.Load(prefs).NewCitiesOpenMilitia);
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(prefs));
            System.IO.File.WriteAllText(prefs,"new\t1\r\nupgrade\t1\r\nother\t1\r\nfloor:1\t0\r\nfloor:2\t0\r\nfloor:3\t0\r\nfloor:4\t0\r\n");
            Check(CityPolicy.Load(prefs).NewCitiesOpenMilitia); // Actual previous 74-byte preferences lack the new key.
            old.Floors[4]=50;old.NewCitiesOpenMilitia=false;old.Save(prefs);
            Check(!System.IO.File.ReadAllText(prefs).Contains("floor:0"));
            System.IO.File.AppendAllText(prefs,"floor:0\t1000\nother\t0\n");
            Check(!System.IO.File.ReadAllText(prefs).Contains("other\t1"));
            var loaded=CityPolicy.Load(prefs);Check(loaded.Floors[0]==0 && loaded.Floor(4)==50 && !loaded.NewCitiesOpenMilitia);
            string production=prefs+".production";
            try {
                Check(CityPolicy.LoadPreferred(production,prefs).Floor(4)==50);
                var current=new CityPolicy();current.Floors[4]=7;current.Save(production);
                Check(CityPolicy.LoadPreferred(production,prefs).Floor(4)==7 && CityPolicy.LoadPreferred(production,prefs).NewCitiesOpenMilitia);
                Check(CityPolicy.Load(prefs).Floor(4)==50);
                Check(CityPolicy.LoadPreferred(production+".absent",prefs+".absent").Floor(4)==0);
            } finally { if(System.IO.File.Exists(production))System.IO.File.Delete(production); }
        }
        finally { if(System.IO.File.Exists(prefs))System.IO.File.Delete(prefs);System.IO.Directory.Delete(System.IO.Path.GetDirectoryName(prefs)); }
    }
    private static void DevelopmentRegressions()
    {
        foreach(string race in new[]{"human","haroun","drauga","gauri","shadow","undead"})
        {
            var final=Upgrade(2,22,202,0,0,0,0,0);final.IsCityCenter=true;final.IsFinalCityUpgrade=true;
            final.Family="def:"+race+"_center_citadel";final.Target="def:"+race+"_center_citadel_militia";
            var income=Upgrade(1,11,101,50,0,0,0,0);var resource=Upgrade(1,12,102,0,10,0,0,0);
            var s=S(income,resource,final);s.Income=new float[]{20,-2,4,4,4};s.Policy.Floors[1]=50;
            Check(Choose(s).Candidate==final); // last center upgrade preempts even a resource shortage
            final.IsFinalCityUpgrade=false;Check(Choose(s).Candidate==resource); // ordinary center is not promoted
            final.IsFinalCityUpgrade=true;s.Construction=new[]{final};Check(Choose(s).Candidate==resource);
            s.Construction=new CityPlanner.Candidate[0];final.Cost=20000;Check(Choose(s).Kind==CityPlanner.DecisionKind.None); // save for the final center
            final.Cost=1;final.Delta[1]=-1;Check(Choose(s).Candidate==resource); // protection still enforced
            final.Delta[1]=0;s.Candidates=new[]{income,final};s.Busy.Add(2);Check(Choose(s).Candidate==income);
            s.Candidates=new[]{resource,income};s.Busy.Add(1);Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        }
        for(int r=1;r<5;r++)foreach(float before in new[]{-10f,0f,5f})
        {
            var fallback=Upgrade(1,11,100,0,0,0,0,0);var gold=Upgrade(2,22,200,10,0,0,0,0);
            var relief=Upgrade(2,23,201,0,0,0,0,0);relief.Delta[r]=1;
            var s=S(fallback,gold,relief);s.Income=new float[]{20,10,10,10,10};s.Income[r]=before;s.Policy.Floors[r]=5;
            Check(Choose(s).Candidate==relief); // ordinary gold remains below target resources
            s.Candidates=new[]{fallback,gold};Check(Choose(s).Candidate==gold);
            s.Candidates=new[]{fallback};Check(Choose(s).Candidate==fallback);
            fallback.Delta[r]=-1;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        }
        // Reported case: iron is -3 and a human market adds -1 iron / +20 gold.
        // Queue/exclusion/cash rules apply; 3 recovered iron saves 12 gold versus 11 from this market.
        var market=C(1,301,125,20,-1,-1,-1,0);market.Target="def:human_market";
        var repair=Upgrade(2,22,302,0,0,0,6,0);
        var state=S(market);state.Income=new float[]{20,0,0,-3,0};
        Check(Choose(state).Candidate==market);
        state.Candidates=new[]{market,repair};Check(Choose(state).Candidate==repair);
        state.Candidates=new[]{market};state.Construction=new[]{C(1,301,125,20,-1,-1,-1,0)};
        Check(Choose(state).Kind==CityPlanner.DecisionKind.None);
        state.Construction=new CityPlanner.Candidate[0];state.Policy.Excluded.Add(1);
        Check(Choose(state).Kind==CityPlanner.DecisionKind.None);state.Policy.Excluded.Clear();
        var planner=new CityPlanner(1);state.Time=0;state.Gold=624;state.Reserve=500;planner.Update(state);state.Time=1;
        Check(planner.Update(state).Kind==CityPlanner.DecisionKind.None && planner.Status==CityPlanner.StatusKind.Gold);
        state.Time=2;state.Gold=625;Check(planner.Update(state).Candidate==market);
    }
    private static void ResourcePriorityRegressions()
    {
        for(int r=1;r<5;r++)foreach(uint kind in new uint[]{13,21})
        foreach(float before in new[]{-5f,0f,4f})
        {
            var resource=Upgrade(2,22,601,0,0,0,0,0);resource.Delta[r]=6;
            var ordinary=Upgrade(1,11,602,1000,0,0,0,0);
            var market=Upgrade(1,12,603,50,0,0,0,0);market.Kind=kind;
            market.Family=kind==21?"def:human_market":"def:human_center_city";
            market.Target=kind==21?"def:human_bank":"def:human_market";market.Delta[r]=-1;
            var s=S(resource,ordinary);s.Income=new float[]{20,10,10,10,10};
            s.Income[r]=before;s.Policy.Floors[r]=5;
            Check(Choose(s).Candidate==resource); // +1000 ordinary gold does not skip resource targets
            s.Candidates=new[]{resource,ordinary,market};
            Check(Choose(s).Candidate==market); // only the market may compete on economic return
            market.Cost=20000;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);market.Cost=50; // save for the winning market
            s.Busy.Add(1);Check(Choose(s).Candidate==resource);s.Busy.Clear();
            s.Policy.Excluded.Add(1);Check(Choose(s).Candidate==resource);s.Policy.Excluded.Clear();
            s.Construction=new[]{market};Check(Choose(s).Candidate==resource);
            s.Construction=new CityPlanner.Candidate[0];
            var center=Upgrade(2,23,604,0,0,0,0,0);center.IsCityCenter=true;center.IsFinalCityUpgrade=true;
            s.Candidates=new[]{resource,ordinary,market,center};Check(Choose(s).Candidate==center);
            // Queued work completes the target. Ordinary gold then belongs to
            // the next stage; cancelling that work restores the resource stage.
            s.Candidates=new[]{resource,ordinary};s.GoalIncome=(float[])s.Income.Clone();s.GoalIncome[r]=6;
            s.Construction=new[]{Upgrade(2,24,605,0,0,0,0,0)};
            Check(Choose(s).Candidate==ordinary);
            s.GoalIncome=null;s.Construction=new CityPlanner.Candidate[0];Check(Choose(s).Candidate==resource);
            s.Candidates=new[]{ordinary,market};Check(Choose(s).Candidate==ordinary); // impossible resource target falls through
            s.UnknownConstruction=true;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        }
        var iron=Upgrade(2,22,701,0,0,0,5,0);
        var bank=Upgrade(1,11,702,24,0,0,-1,0);bank.Family="def:human_market";bank.Target="def:human_bank";
        var weak=Upgrade(1,11,703,5,0,0,100,0);weak.Family=bank.Family;weak.Target="def:human_bazaar";
        var state=S(iron,bank,weak);state.Income=new float[]{30,10,10,-5,10};state.Policy.Floors[3]=10;
        Check(Choose(state).Candidate==iron); // 20 saved versus 24-4: equality keeps resource progress
        bank.Delta[0]=23;Check(Choose(state).Candidate==iron);
        bank.Delta[0]=25;Check(Choose(state).Candidate==bank);
        bank.Cost=20000;Check(Choose(state).Kind==CityPlanner.DecisionKind.None); // save for best market; weak fork stays forbidden
        bank.Cost=50;state.Candidates=new[]{weak};weak.Delta[0]=0;
        Check(Choose(state).Kind==CityPlanner.DecisionKind.None); // resource stage
        state.Income[3]=20;Check(Choose(state).Kind==CityPlanner.DecisionKind.None); // random stage
        var fallback=Upgrade(2,22,704,0,0,0,0,0);state.Candidates=new[]{weak,fallback};
        Check(Choose(state).Candidate==fallback);
    }
    private static void SavingPriorityRegressions()
    {
        // Replay the reported 49:50 situation: queued work still leaves mana
        // at -9; cheap exports/barracks must not drain savings for mana income.
        var library=C(2,801,120,0,0,0,0,3);
        var college=Upgrade(2,22,802,5,0,0,0,4);college.Cost=125;
        var export=Upgrade(1,11,803,18,0,-2,0,0);export.Cost=95;
        var barracks=C(1,804,80,0,0,0,0,0);
        var s=S(library,college,export,barracks);s.Reserve=0;s.Gold=78;
        s.Income=new float[]{530,33,19,21,-9};s.GoalIncome=new float[]{572,29,17,27,-9};
        var p=new CityPlanner(1);p.Update(s);
        foreach(float cash in new[]{78f,80f,95f,120f,124f})
        {
            s.Time++;s.Gold=cash;
            Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
            Check(p.Status==CityPlanner.StatusKind.Gold && p.Next==college && p.Explanation=="resources");
        }
        s.Time++;s.Gold=125;Check(p.Update(s).Candidate==college);

        // All four targets, construction/upgrade and zero/nonzero reserves.
        // Neither ordinary gold nor random affordable work may skip saving.
        for(int r=1;r<5;r++)foreach(uint kind in new uint[]{13,21})
        foreach(uint reserve in new uint[]{0,500})
        {
            var resource=Upgrade(2,22,811,0,0,0,0,0);resource.Kind=kind;resource.Cost=125;resource.Delta[r]=4;
            var cheap=Upgrade(1,11,812,20,0,0,0,0);cheap.Cost=40;
            s=S(resource,cheap);s.Income=new float[]{100,10,10,10,10};s.Income[r]=-9;
            s.Reserve=reserve;s.Gold=reserve+40;p=new CityPlanner(1);p.Update(s);
            foreach(float cash in new[]{40f,100f,124.5f})
            {
                s.Time++;s.Gold=reserve+cash;
                Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==resource && p.Status==CityPlanner.StatusKind.Gold);
            }
            s.Time++;s.Gold=reserve+125;Check(p.Update(s).Candidate==resource);
            // Accepted manual work now covers the target; waiting must stop.
            p=new CityPlanner(1);s.Time=0;s.Gold=reserve+40;p.Update(s);s.Time=1;p.Update(s);
            s.Construction=new[]{resource};s.GoalIncome=(float[])s.Income.Clone();s.GoalIncome[r]=1;s.Time++;
            Check(p.Update(s).Candidate==cheap);
            // Cancelled work restores the resource priority without a stale goal.
            p=new CityPlanner(1);s.Time=0;p.Update(s);s.Construction=new CityPlanner.Candidate[0];s.GoalIncome=null;s.Time++;
            Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==resource);
            // Truly unavailable options do not stall the other stages.
            s.Policy.Excluded.Add(2);s.Time++;Check(p.Update(s).Candidate==cheap);
        }

        // A winning market is saved for; a weaker affordable branch is never
        // substituted. Losing/tied markets cannot spend the resource savings.
        var repair=Upgrade(2,22,821,0,0,0,0,4);repair.Cost=120;
        var bank=Upgrade(1,11,822,40,0,0,0,-1);bank.Cost=200;bank.Family="def:human_market";
        var weak=Upgrade(1,11,823,5,0,0,0,20);weak.Cost=20;weak.Family=bank.Family;
        s=S(repair,bank,weak);s.Income=new float[]{100,10,10,10,-9};s.Reserve=0;s.Gold=120;
        p=new CityPlanner(1);p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==bank && p.Explanation=="market_over_resources");
        s.Gold=200;s.Time++;Check(p.Update(s).Candidate==bank);
        foreach(float directGold in new[]{24f,25f})
        {
            bank.Delta[0]=directGold;bank.Cost=20;s.Gold=100;s.Time=0;p=new CityPlanner(1);p.Update(s);s.Time=1;
            Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==repair && p.Explanation=="resources");
        }

        // Final centers and gold development retain their priority while saving.
        var center=Upgrade(2,22,831,0,0,0,0,0);center.Cost=150;center.IsCityCenter=true;center.IsFinalCityUpgrade=true;
        s=S(center,repair);s.Income=new float[]{100,10,10,10,-9};s.Reserve=0;s.Gold=120;
        p=new CityPlanner(1);p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==center && p.Explanation=="final_city_upgrade");
        s.Gold=150;s.Time++;Check(p.Update(s).Candidate==center);
        var gold=Upgrade(2,22,832,30,0,0,0,0);gold.Cost=150;
        s=S(gold,barracks);s.Income=new float[]{100,10,10,10,10};s.Reserve=0;s.Gold=80;
        p=new CityPlanner(1);p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==gold && p.Explanation=="net_gold");
        s.Gold=150;s.Time++;Check(p.Update(s).Candidate==gold);

        // Equivalent actions can still start in another city, at the SAME
        // priority and benefit, without saving unnecessarily for the dearer one.
        var same=Upgrade(1,11,833,30,0,0,0,0);same.Cost=50;
        s=S(gold,same);s.Income=new float[]{100,10,10,10,10};s.Reserve=0;s.Gold=50;
        p=new CityPlanner(1);p.Update(s);s.Time=1;Check(p.Update(s).Candidate==same);

        // Every observation rechecks policy/ownership/queue, not only cash.
        foreach(string change in new[]{"busy","lost","excluded","queued","removed","goal","reserve","unknown"})
        {
            s=S(repair,barracks);s.Income=new float[]{100,10,10,10,-9};s.Reserve=0;s.Gold=80;
            p=new CityPlanner(1);p.Update(s);s.Time=1;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Next==repair);
            if(change=="busy")s.Busy.Add(2);
            if(change=="lost")s.Cities=new uint[]{1};
            if(change=="excluded")s.Policy.Excluded.Add(2);
            if(change=="queued")s.Construction=new[]{repair};
            if(change=="removed")s.Candidates=new[]{barracks};
            if(change=="goal")s.GoalIncome=new float[]{100,10,10,10,1};
            if(change=="reserve"){s.Reserve=100;s.Gold=120;}
            if(change=="unknown")s.UnknownConstruction=true;
            s.Time++;
            var d=p.Update(s);
            if(change=="reserve")Check(d.Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Gold && p.Next==repair);
            else if(change=="unknown")Check(d.Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Construction && p.Next==null);
            else Check(d.Candidate==barracks);
        }
    }
    private static void NetIncomeRegressions()
    {
        var bank=Upgrade(1,11,401,40,-1,-1,-1,0);bank.Family="def:human_market";bank.Target="def:human_bank";
        var bazaar=Upgrade(1,11,402,5,3,3,3,0);bazaar.Family=bank.Family;bazaar.Target="def:human_bazaar";
        var iron=Upgrade(2,22,403,0,0,0,6,0);
        var s=S(bank,bazaar,iron);s.Income=new float[]{20,-1,-1,-3,0};
        Check(CityPlanner.NetGoldGain(bank,s.Income,s.ShortageCost)==31);
        Check(CityPlanner.NetGoldGain(bazaar,s.Income,s.ShortageCost)==22);
        Check(CityPlanner.NetGoldGain(iron,s.Income,s.ShortageCost)==12);
        Check(Choose(s).Candidate==bank);
        // A richer resource fork must NEVER consume the market's gold branch.
        bazaar.Delta[3]=100;s.Income[3]=-100;
        Check(Choose(s).Candidate==bank); // mine +24, bank +31; bazaar forbidden
        iron.Delta[3]=10;Check(Choose(s).Candidate==iron); // recovered iron saves 40 gold
        // Construction of a market is compared on the same basis as upgrades.
        bank.Kind=13;bank.Actor=11;bank.Target="def:human_market";s.Candidates=new[]{bank,iron};
        Check(Choose(s).Candidate==iron);
        s.GoalIncome=new float[]{20,-1,-1,4,0};
        s.Construction=new[]{Upgrade(2,23,499,0,0,0,104,0)};
        Check(Choose(s).Candidate==bank); // accepted mine will already cover iron
        Check(CityPlanner.NetGoldGain(bank,s.GoalIncome,s.ShortageCost)==35);
        s.GoalIncome=new float[]{20,-1,-1,-20,0};Check(Choose(s).Candidate==iron);
        // Cancellation/completion must recalculate without a stale reservation.
        s.GoalIncome=null;s.Construction=new CityPlanner.Candidate[0];s.Income[3]=4;
        Check(Choose(s).Candidate==bank);
        s.Income[3]=-2;bank.Delta[0]=1;s.Candidates=new[]{bank};
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None); // loss-making exchange is not random fallback
        // No positive market branch => leave it alone, even if it gives resources.
        bank.Kind=21;bank.Family="def:human_market";bank.Target="def:human_bank";
        foreach(float gain in new[]{0f,-1f})
        {
            bank.Delta=new float[]{gain,20,20,20,20};s.Candidates=new[]{bank};
            Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        }
        bank.Delta=new float[]{40,-1,-1,-1,0};bazaar.Delta=new float[]{5,3,3,3,0};
        s.Candidates=new[]{bank,bazaar};bank.Cost=20000;
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None); // don't buy cheap weak branch
        bank.Cost=50;s.Construction=new[]{bank};
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None); // no duplicate/alternative during upgrade
        s.Construction=new CityPlanner.Candidate[0];
        // Rates are engine data, including fractional rates and free resources.
        for(int r=1;r<5;r++)foreach(float rate in new[]{0f,.5f,2f,9f})
        {
            var repair=Upgrade(2,22,500,0,0,0,0,0);repair.Delta[r]=10;
            s=S(repair);s.Income=new float[]{20,0,0,0,0};s.Income[r]=-3;s.ShortageCost[r]=rate;
            Check(CityPlanner.NetGoldGain(repair,s.Income,s.ShortageCost)==3*rate);
            s.Income[r]=2;Check(CityPlanner.NetGoldGain(repair,s.Income,s.ShortageCost)==0);
            s.ShortageCost[r]=float.NaN;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        }
        s=S(bank);s.ShortageCost=null;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
    }
}
