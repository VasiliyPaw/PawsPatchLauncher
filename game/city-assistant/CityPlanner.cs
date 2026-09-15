using System;
using System.Collections.Generic;
using System.Linq;

// Pure local intention queue. It does not modify the game or consume its RNG.
internal sealed class CityPlanner
{
    internal sealed class Candidate
    {
        internal uint City, Actor, Data, Kind;
        internal uint CityAddress; // Read-only presentation hint, never used for orders.
        internal float Cost;
        internal float[] Delta;
        internal string Name = "", SourceName = "", Family = "", Target = "";
        internal int BranchCount;
        internal bool IsCityCenter, IsMine, IsFinalCityUpgrade;
        internal bool Same(Candidate b) { return b != null && City == b.City && Actor == b.Actor && Data == b.Data && Kind == b.Kind; }
    }
    internal sealed class Snapshot
    {
        internal uint Epoch, Reserve;
        internal float Time, Gold;
        internal bool Enabled, Valid; // Valid permits new spending, not snapshot observation.
        internal uint[] Cities;
        internal HashSet<uint> Busy = new HashSet<uint>(); // Siege/sale/invalid actor, never another building's construction.
        internal float[] Income;
        // Gold charged for a unit of upkeep shortage, from live Resource definitions.
        internal float[] ShortageCost;
        internal Candidate[] Candidates;
        internal CityPolicy Policy = new CityPolicy();
        // Forecast includes only adverse outstanding deltas: future gains may
        // not fund another order before they actually enter the economy.
        internal float[] Forecast;
        // Includes expected gains only for choosing goals, never for protection
        // or affordability. Exact native work records acknowledge paid orders.
        internal float[] GoalIncome;
        internal Candidate[] Construction = new Candidate[0];
        internal bool UnknownConstruction;
    }
    internal enum DecisionKind { None, Submit, Fault }
    internal sealed class Decision
    {
        internal DecisionKind Kind;
        internal Candidate Candidate;
        internal string Reason;
    }
    private readonly Random random;
    private readonly List<uint> queue = new List<uint>();
    private readonly Dictionary<uint, float> backoff = new Dictionary<uint, float>();
    private uint epoch;
    private float previousTime = -1, pendingSince, cooldownUntil;
    private Candidate intention, pending;
    private bool awaitingReply, fault, wasEnabled;
    internal enum StatusKind { Waiting, Off, Editing, Paused, Gold, Pending, Busy, NoChoices, NoCities, Fault, Protected, Construction }
    internal StatusKind Status { get; private set; }
    internal string Explanation { get; private set; }
    internal Candidate Next { get { return pending ?? intention; } }
    internal CityPlanner(int seed) { random = new Random(seed); }
    internal static bool Finite(float v) { return !float.IsNaN(v) && !float.IsInfinity(v); }
    private static bool Safe(Candidate c, int resources)
    {
        return c != null && (c.Kind == 13 || c.Kind == 21) && c.City != 0 && c.Actor != 0 && c.Data != 0
            && Finite(c.Cost) && c.Cost >= 0 && c.Delta != null && c.Delta.Length == resources && c.Delta.All(Finite);
    }
    internal void Reset()
    {
        queue.Clear(); backoff.Clear(); intention = null; pending = null;
        awaitingReply = false; fault = false; cooldownUntil = 0;
    }
    private void Rotate(uint city)
    {
        queue.Remove(city); queue.Add(city); intention = null;
    }
    internal void Reply(bool sent, float gameTime)
    {
        if (!awaitingReply || pending == null) return;
        awaitingReply = false;
        if (sent) { pendingSince = gameTime; Rotate(pending.City); }
        else { backoff[pending.City] = gameTime + 5; Rotate(pending.City); pending = null; }
    }
    internal Decision Update(Snapshot s)
    {
        Status = StatusKind.Waiting;
        Explanation = "";
        Decision none = new Decision();
        if (s == null || s.Cities == null || s.Candidates == null || s.Income == null
            || !Finite(s.Time) || !Finite(s.Gold) || !s.Income.All(Finite)) { intention = null; return none; }
        bool advances = previousTime >= 0 && s.Time > previousTime;
        if (s.Epoch != epoch || s.Time < previousTime)
        {
            Reset(); epoch = s.Epoch; advances = false;
        }
        previousTime = s.Time;
        // Observe already-sent work even while disabled or while editing reserve.
        // Switching off cancels intentions, not accepted native construction.
        if (pending != null && !awaitingReply && Started(s,pending))
        { pending = null; cooldownUntil = s.Time + .5f; }
        if (pending != null && !s.Cities.Contains(pending.City))
        { pending = null; awaitingReply = false; }
        if (!s.Enabled || !s.Valid)
        {
            Status = !s.Enabled ? StatusKind.Off : StatusKind.Editing;
            intention = null;
            if (!s.Enabled) { queue.Clear(); backoff.Clear(); fault = false; }
            wasEnabled = s.Enabled;
            // An already submitted engine order is not cancelled by this switch.
            return none;
        }
        if (!wasEnabled) { fault = false; wasEnabled = true; }
        queue.RemoveAll(c => !s.Cities.Contains(c));
        foreach (uint city in s.Cities) if (!queue.Contains(city)) queue.Add(city);
        if (pending != null)
        {
            if (!s.Cities.Contains(pending.City)) { pending = null; awaitingReply = false; }
            else if (awaitingReply) { Status = StatusKind.Pending; return none; }
            else if (Started(s,pending)) { pending = null; cooldownUntil = s.Time + .5f; }
            else if (s.Time - pendingSince >= 10)
            {
                pending = null; intention = null; fault = true;
                Status = StatusKind.Fault;
                return new Decision { Kind = DecisionKind.Fault, Reason = "construction_not_confirmed" };
            }
            else { Status = StatusKind.Pending; return none; }
        }
        if (!advances || fault || s.Time < cooldownUntil)
        { Status = fault ? StatusKind.Fault : !advances ? StatusKind.Paused : StatusKind.Waiting; return none; }
        if (s.UnknownConstruction) { intention = null; Status = StatusKind.Construction; return none; }
        float[] projected = s.Forecast ?? s.Income;
        float[] goals = s.GoalIncome ?? projected;
        if (projected.Length != s.Income.Length || !projected.All(Finite)
            || goals.Length != s.Income.Length || !goals.All(Finite)) { intention = null; return none; }
        if (s.ShortageCost == null || s.ShortageCost.Length < s.Income.Length
            || s.ShortageCost.Any(v => !Finite(v) || v < 0)) { intention = null; return none; }
        CityPolicy policy = s.Policy ?? new CityPolicy();
        Candidate[] available = s.Candidates.Where(c => Safe(c, s.Income.Length) && s.Cities.Contains(c.City)
            && !s.Busy.Contains(c.City) && (!backoff.ContainsKey(c.City) || s.Time >= backoff[c.City])
            && !InProgress(s,c) && policy.Allows(c)).ToArray();
        // Filter irreversible market branches BEFORE affordability. A cheaper
        // weaker branch must not replace the best one while saving for it.
        Candidate[] eligible = available.Where(c => BestMarketBranch(c, available)
            && Protects(c, s.Income, projected, policy)
            && (!IsMarket(c) || NetGoldGain(c, goals, s.ShortageCost) > .0001)).ToArray();
        // Lack of cash is temporary, not an unavailable development path.
        // Rank every legal action first; cheaper lower priorities must not
        // consume the savings needed for a center, resource target or market.
        // Resource targets precede ordinary gold development. Only a market
        // may replace the selected resource action when its net return wins.
        // All accepted construction is included in goals at every stage.
        double gain = eligible.Length == 0 ? 0 : eligible.Max(c => NetGoldGain(c, goals, s.ShortageCost));
        Candidate[] resources = eligible.Where(c => !IsMarket(c) && Relief(c, goals, policy) > .0001).ToArray();
        Candidate[] priority;
        var finalCenters=eligible.Where(c=>c.Kind==21 && c.IsCityCenter && c.IsFinalCityUpgrade).ToArray();
        if(finalCenters.Length>0) { priority=finalCenters; Explanation="final_city_upgrade"; }
        else if (resources.Length > 0)
        {
            double relief = resources.Max(c => Relief(c, goals, policy));
            priority = resources.Where(c => Relief(c, goals, policy) >= relief - .0001).ToArray();
            double resourceGain = priority.Max(c => NetGoldGain(c, goals, s.ShortageCost));
            priority = priority.Where(c => NetGoldGain(c, goals, s.ShortageCost) >= resourceGain - .0001).ToArray();
            Explanation = "resources";
            Candidate[] markets = eligible.Where(IsMarket).ToArray();
            double marketGain = markets.Length == 0 ? 0 : markets.Max(c => NetGoldGain(c, goals, s.ShortageCost));
            // Equal returns keep resource progress. No other gold building is
            // allowed into this comparison, even if it earns more than either.
            if (marketGain > .0001 && marketGain > resourceGain + .0001)
            {
                priority = markets.Where(c => NetGoldGain(c, goals, s.ShortageCost) >= marketGain - .0001).ToArray();
                Explanation = "market_over_resources";
            }
        }
        else if (gain > .0001)
        {
            priority = eligible.Where(c => NetGoldGain(c, goals, s.ShortageCost) >= gain - .0001).ToArray();
            // Equal economic returns may still move income towards the targets.
            double tieRelief = priority.Max(c => Relief(c, goals, policy));
            priority = priority.Where(c => Relief(c, goals, policy) >= tieRelief - .0001).ToArray();
            Explanation = "net_gold";
        }
        else
        {
            float gold = eligible.Length == 0 ? 0 : eligible.Max(c => c.Delta[0]);
            if (gold > .0001f) { priority = eligible.Where(c => c.Delta[0] >= gold - .0001f).ToArray(); Explanation = "gold"; }
            else
            {
                double best=eligible.Length==0?0:eligible.Max(c=>GoldPreparation(c,available,goals,goals,policy));
                priority=best>.0001?eligible.Where(c=>GoldPreparation(c,available,goals,goals,policy)>=best-.0001).ToArray():new Candidate[0];
                Explanation="prepare_gold";
                if(priority.Length==0)
                {
                    // The engine still validates each order. This includes
                    // non-economic buildings, centers and surplus mine upgrades.
                    // Unreachable income targets must not freeze development.
                    // Forecasts, exclusions and protection were already
                    // checked; queued work is never scheduled twice.
                    priority=eligible;
                    Explanation="random";
                }
            }
        }
        // Equally useful actions in this selected priority may start in another
        // city now. Otherwise retain a waiting intention from this priority and
        // save for it. Fresh snapshots still invalidate changed/fulfilled goals.
        Candidate[] affordable = priority.Where(c => (double)s.Gold >= (double)s.Reserve + c.Cost).ToArray();
        if (affordable.Length > 0) priority = affordable;
        for (int visited = 0; visited < queue.Count; visited++)
        {
            uint city = queue[0]; float until;
            if (s.Busy.Contains(city) || (backoff.TryGetValue(city, out until) && s.Time < until)) { Rotate(city); continue; }
            Candidate[] legal = priority.Where(c => c.City == city).ToArray();
            if (legal.Length == 0) { Rotate(city); continue; }
            Candidate selected = legal.FirstOrDefault(c => c.Same(intention)) ??
                (Explanation=="random" ? legal[random.Next(legal.Length)] : legal.OrderBy(c => c.Cost).ThenBy(c => c.Data).First());
            intention = selected;
            // Wait without falling through to a lower priority. The native
            // dispatcher repeats every payment/reserve check before spending.
            if ((double)s.Gold < (double)s.Reserve + selected.Cost) { Status = StatusKind.Gold; return none; }
            pending = selected; awaitingReply = true; pendingSince = s.Time;
            Status = StatusKind.Pending;
            return new Decision { Kind = DecisionKind.Submit, Candidate = selected };
        }
        intention = null;
        Status = s.Cities.Length == 0 ? StatusKind.NoCities : s.Cities.All(c => s.Busy.Contains(c)) ? StatusKind.Busy
            : backoff.Any(p => s.Time < p.Value) ? StatusKind.Waiting : s.Candidates.Length > 0 ? StatusKind.Protected : StatusKind.NoChoices;
        return none;
    }
    private static bool Started(Snapshot s,Candidate pending)
    {
        // A siege or an unrelated manual order is NOT an acknowledgement.
        // New construction gets a new actor ID; upgrades keep the source actor
        // until completion. Both must match the exact requested definition.
        return s.Construction!=null && s.Construction.Any(c=>c!=null && c.City==pending.City
            && c.Data==pending.Data && c.Kind==pending.Kind && (pending.Kind==13 || c.Actor==pending.Actor));
    }
    private static bool InProgress(Snapshot s,Candidate candidate)
    {
        return s.Construction!=null && s.Construction.Any(c=>c!=null && c.City==candidate.City &&
            (candidate.Kind==13 ? c.Data==candidate.Data : c.Actor==candidate.Actor));
    }
    internal static bool IsMarket(Candidate c)
    {
        return c!=null && ((c.Family??"").EndsWith("_market",StringComparison.Ordinal)
            || (c.Target??"").EndsWith("_market",StringComparison.Ordinal));
    }
    internal static bool BestMarketBranch(Candidate c, Candidate[] available)
    {
        if (c.Kind != 21 || !IsMarket(c)) return true;
        return c.Delta[0] > 0 && !available.Any(other => other.Kind == 21
            && other.City == c.City && other.Actor == c.Actor && IsMarket(other)
            && other.Delta[0] > c.Delta[0]);
    }
    internal static double NetGoldGain(Candidate c, float[] income, float[] shortageCost)
    {
        double gain = c.Delta[0];
        for (int i = 1; i < Math.Min(5, income.Length); i++)
        {
            double before = Math.Max(0, -(double)income[i]);
            double after = Math.Max(0, -((double)income[i] + c.Delta[i]));
            gain += (before - after) * shortageCost[i];
        }
        return gain;
    }
    private static double GoldPreparation(Candidate provider,Candidate[] available,float[] current,float[] forecast,CityPolicy policy)
    {
        if(provider.Kind!=21 || provider.IsCityCenter) return 0;
        double best=0;
        foreach(var gold in available)
        {
            if(gold.Delta[0]<=.0001f || gold.Actor==provider.Actor || Protects(gold,current,forecast,policy)) continue;
            // Avoid spending a branch for an economically losing exchange.
            if(gold.Delta[0]+provider.Delta[0]<=.0001f) continue;
            double before=0,after=0;
            for(int i=1;i<Math.Min(5,current.Length);i++)
            {
                float income=Math.Min(current[i],forecast[i]);
                before+=Math.Max(0,policy.Floor(i)-(income+gold.Delta[i]));
                after+=Math.Max(0,policy.Floor(i)-(income+provider.Delta[i]+gold.Delta[i]));
            }
            // Partial preparation is permitted when a market needs several
            // resources, but every step must strictly reduce that shortfall.
            if(before>after+.0001) best=Math.Max(best,(before-after)*gold.Delta[0]);
        }
        return best;
    }
    internal static bool Protects(Candidate c, float[] current, float[] forecast, CityPolicy policy)
    {
        // A profitable market may trade more resource upkeep for gold even
        // when that resource is already below its target or in deficit.
        bool marketException=IsMarket(c) && c.Delta!=null && c.Delta.Length>0
            && Finite(c.Delta[0]) && c.Delta[0]>0;
        // The verified 1.3.72 resource list starts with gold/stone/wood/iron/mana.
        // Unit-count and kingdom-count bookkeeping are not resource income.
        for (int i = 0; i < Math.Min(5, current.Length); i++)
        {
            if(i>0 && marketException) continue;
            float floor = policy.Floor(i);
            float before = Math.Min(current[i], forecast[i]);
            if (c.Delta[i] < -.0001f && before + c.Delta[i] < Math.Min(before, floor) - .0001f) return false;
        }
        return true;
    }
    private static double Relief(Candidate c, float[] income, CityPolicy policy)
    {
        double sum = 0;
        for (int i = 1; i < Math.Min(5, income.Length); i++)
            if (income[i] <= policy.Floor(i)) sum += Math.Min(Math.Max(0, c.Delta[i]), Math.Max(1, policy.Floor(i) - income[i]));
        return sum;
    }
}
