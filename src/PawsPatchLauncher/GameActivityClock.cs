namespace PawsPatchLauncher;

// One local display clock. Network cadence is unchanged. The authoritative
// sample corrects the estimate; stale/offline activity must not run forever.
public sealed class GameActivityClock
{
    private DateTimeOffset? observed;
    private long anchor;
    private double initialAge;
    private int? seconds;
    private bool running;
    public void Observe(GameActivityDetails details, long monotonic, DateTimeOffset now)
    {
        if (observed is not null && details.ObservedAt <= observed) return;
        observed = details.ObservedAt; anchor = monotonic;
        initialAge = Math.Clamp((now - details.ObservedAt).TotalSeconds, 0, 40);
        seconds = details.Activity.ElapsedSeconds;
        running = details.Activity.Phase == "match";
    }
    public int? Seconds(long monotonic)
    {
        if (seconds is null) return null;
        var age = Math.Min(40, initialAge + Math.Max(0, monotonic - anchor) / 1000d);
        return seconds + (running ? (int)age : 0);
    }
    public static string Format(int seconds)
    {
        var time = TimeSpan.FromSeconds(Math.Max(0, seconds));
        return time.TotalHours >= 1 ? $"{(int)time.TotalHours}:{time.Minutes:00}:{time.Seconds:00}" : $"{time.Minutes:00}:{time.Seconds:00}";
    }
}
