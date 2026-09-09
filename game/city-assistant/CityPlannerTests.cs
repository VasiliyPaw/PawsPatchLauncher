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
        foreach(var c in s.Candidates){c.Kind=21;c.Family="barracks";c.Target="advanced";}
        for(int i=1;i<40;i++){s.Time=i;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);}
        s.Gold=570;s.Time++;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
        s.Policy.AllowOther=true;s.Time++;Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);
        // Switching off during accepted work still observes the acknowledgement.
        p=new CityPlanner(4);s=S(C(1,100,70,1,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.Submit);p.Reply(true,1);
        s.Enabled=false;s.Time=2;s.Busy.Add(1);s.Construction=s.Candidates;Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
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
        s.Valid=false;s.Time=2;s.Busy.Add(1);s.Construction=s.Candidates;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Editing);
        s.Time=20;s.Busy.Clear();Check(p.Update(s).Kind==CityPlanner.DecisionKind.None);
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
        // A different city can repair the deficit and takes priority over gold.
        p=new CityPlanner(1);s=S(C(1,100,0,100,0),C(2,200,0,0,1));p.Update(s);s.Time=1;
        Check(p.Update(s).Candidate.City==2);
        // Gold-producing branch that deepens the iron shortage must never win.
        p=new CityPlanner(1);s=S(C(1,100,0,50,-1));p.Update(s);s.Time=1;
        Check(p.Update(s).Kind==CityPlanner.DecisionKind.None && p.Status==CityPlanner.StatusKind.Protected);
        // Resource targets matter before an actual deficit begins.
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
        EconomyRegressions();
        ParallelRegressions();
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
            Check(Choose(s).Candidate.Data==101);
            s.Busy.Add(1);Check(Choose(s).Candidate.Data==200);
            s.Busy.Clear();s.Policy.Excluded.Add(1);Check(Choose(s).Candidate.Data==200);
            // Ongoing work already covers target: don't build duplicate relief.
            s.Policy.Excluded.Clear();s.GoalIncome=(float[])income.Clone();s.GoalIncome[r]=3;
            Check(Choose(s).Candidate.Data==200);
            // ...but its future positive income cannot finance a gold fork yet.
            effect[r]=-1;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
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
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
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
        s.Policy.Floors[3]=5;s.Policy.AllowOther=true;
        Check(Choose(s).Kind==CityPlanner.DecisionKind.None); // not more iron on the same fork
        s.Policy.Floors[3]=12;Check(Choose(s).Candidate==more);
        s.Policy.Floors[3]=0;s.Income=new float[]{400,278,150,104,104};s.Policy.Floors[4]=50;
        Check(Choose(s).Candidate==gold);
        s.Candidates=new[]{more};Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        // New construction, then city expansion, before surplus resource upgrades.
        var secondGold=Upgrade(2,22,200,20,0,0,-2,0);
        s=S(more,secondGold,C(1,300,20,0,0,0,0,0));s.Income=new float[]{30,0,0,6,60};s.Policy.Floors[3]=5;
        Check(Choose(s).Candidate.Data==300);
        s.Candidates[2].Kind=21;s.Candidates[2].Family="center";s.Candidates[2].Target="city";s.Candidates[2].IsCityCenter=true;
        Check(Choose(s).Candidate.Data==300);
        s.Candidates=new[]{more,secondGold};Check(Choose(s).Candidate==more);
        s.Income[3]+=6;s.Candidates=new[]{secondGold};Check(Choose(s).Candidate==secondGold);
        // A provider cannot irreversibly consume the actor needed by the gold branch.
        s.Candidates=new[]{more,gold};s.Income[3]=6;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        // All supported market families: +5 with upkeep refund is never a fallback.
        foreach(string race in new[]{"human","drauga","gauri","haroun","shadow","undead","human_sovereign","gauri_miningpost"})
        {
            var bank=Upgrade(1,11,100,5,1,1,1,0);bank.Family="def:"+race+"_market";
            var bazaar=Upgrade(1,11,101,40,-3,-3,-3,0);bazaar.Family=bank.Family;
            s=S(bank,bazaar);s.Income=new float[]{100,3,3,3,60};s.Policy.AllowOther=true;
            Check(Choose(s).Candidate==bazaar);
            s.Policy.Floors[1]=1;Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
            s.Candidates=new[]{bank};Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
            bank.Delta=new float[]{-5,8,6,4,2};bazaar.Delta=new float[]{-30,9,7,6,4};
            s.Candidates=new[]{bank,bazaar};s.Policy.Floors[1]=20;
            Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        }
        // Several resources can be prepared for a blocked market, one completed
        // building at a time, without upgrading resources unrelated to its needs.
        var market=Upgrade(2,22,200,40,-3,-3,-3,0);market.Family="def:human_market";
        var stone=Upgrade(1,11,101,0,3,0,0,0);var mana=Upgrade(1,12,102,0,0,0,0,8);
        s=S(market,stone,mana);s.Income=new float[]{30,1,1,1,104};
        Check(Choose(s).Candidate==stone);
        s.Income[1]=4;s.Candidates=new[]{market,mana};Check(Choose(s).Kind==CityPlanner.DecisionKind.None);
        // Removed gold target must not remain active from old preferences.
        var old=new CityPolicy();old.Floors[0]=1000;Check(old.Floor(0)==0);
        Check(CityPlanner.Protects(C(1,100,0,-1,0,0,0,3),new float[]{30,0,0,0,0},new float[]{30,0,0,0,0},old));
        string prefs=System.IO.Path.Combine(System.IO.Path.GetTempPath(),"paw-policy-test-"+Guid.NewGuid().ToString("N"),"policy.ini");
        try
        {
            old.Floors[4]=50;old.AllowOther=true;old.Save(prefs);
            Check(!System.IO.File.ReadAllText(prefs).Contains("floor:0"));
            System.IO.File.AppendAllText(prefs,"floor:0\t1000\n");
            var loaded=CityPolicy.Load(prefs);Check(loaded.Floors[0]==0 && loaded.Floor(4)==50 && loaded.AllowOther);
            string production=prefs+".production";
            try {
                Check(CityPolicy.LoadPreferred(production,prefs).Floor(4)==50);
                var current=new CityPolicy();current.Floors[4]=7;current.Save(production);
                Check(CityPolicy.LoadPreferred(production,prefs).Floor(4)==7);
                Check(CityPolicy.Load(prefs).Floor(4)==50);
                Check(CityPolicy.LoadPreferred(production+".absent",prefs+".absent").Floor(4)==0);
            } finally { if(System.IO.File.Exists(production))System.IO.File.Delete(production); }
        }
        finally { if(System.IO.File.Exists(prefs))System.IO.File.Delete(prefs);System.IO.Directory.Delete(System.IO.Path.GetDirectoryName(prefs)); }
    }
}
