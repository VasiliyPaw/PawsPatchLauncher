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
        internal bool Same(Candidate b) { return b != null && City == b.City && Actor == b.Actor && Data == b.Data && Kind == b.Kind; }
    }
    internal sealed class Snapshot
    {
        internal uint Epoch, Reserve;
        internal float Time, Gold;
        internal bool Enabled, Valid; // Valid permits new spending, not snapshot observation.
        internal uint[] Cities;
        internal HashSet<uint> Busy = new HashSet<uint>();
        internal float[] Income;
        internal Candidate[] Candidates;
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
    internal enum StatusKind { Waiting, Off, Editing, Paused, Gold, Pending, Busy, NoChoices, NoCities, Fault }
    internal StatusKind Status { get; private set; }
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
        if (pending != null && !awaitingReply && s.Busy.Contains(pending.City))
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
            else if (s.Busy.Contains(pending.City)) { pending = null; cooldownUntil = s.Time + .5f; }
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
        for (int visited = 0; visited < queue.Count; visited++)
        {
            uint city = queue[0]; float until;
            if (s.Busy.Contains(city) || (backoff.TryGetValue(city, out until) && s.Time < until)) { Rotate(city); continue; }
            Candidate[] legal = s.Candidates.Where(c => c.City == city && Safe(c, s.Income.Length)).ToArray();
            if (legal.Length == 0) { Rotate(city); continue; }
            Candidate selected = Choose(legal, s.Income, intention);
            intention = selected;
            // Do not skip an expensive head item in favour of cheaper later cities.
            if ((double)s.Gold < (double)s.Reserve + selected.Cost) { Status = StatusKind.Gold; return none; }
            pending = selected; awaitingReply = true; pendingSince = s.Time;
            Status = StatusKind.Pending;
            return new Decision { Kind = DecisionKind.Submit, Candidate = selected };
        }
        Status = s.Cities.Length == 0 ? StatusKind.NoCities : s.Cities.All(c => s.Busy.Contains(c)) ? StatusKind.Busy
            : backoff.Any(p => s.Time < p.Value) ? StatusKind.Waiting : StatusKind.NoChoices;
        return none;
    }
    private Candidate Choose(Candidate[] candidates, float[] income, Candidate keep)
    {
        Func<Candidate,double> deficit = c => Enumerable.Range(0,income.Length)
            .Where(i => income[i] < 0)
            .Sum(i => Math.Min(c.Delta[i],-income[i]));
        double best = candidates.Max(deficit);
        Candidate[] pool;
        if (best > 0) pool = candidates.Where(c => deficit(c) == best).ToArray();
        else
        {
            float gold = candidates.Max(c => c.Delta[0]);
            pool = gold > 0 ? candidates.Where(c => c.Delta[0] == gold).ToArray() : candidates;
        }
        // Preserve a waiting choice only while it is still in the best priority
        // group. New deficits caused by manual actions override a gold intention.
        return pool.FirstOrDefault(c => c.Same(keep)) ?? pool[random.Next(pool.Length)];
    }
}
