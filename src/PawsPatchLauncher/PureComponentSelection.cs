namespace PawsPatchLauncher;

/// <summary>Independent preferences for the optional Vanilla/Immortals beta features.</summary>
public sealed class PureComponentSelection
{
    public bool Colors { get; set; }
    public bool IgnoreDesync { get; set; }
    public bool? SuspendedColors { get; set; }
    public bool? SuspendedDesync { get; set; }

    public void Enable(bool enabled)
    {
        if (!enabled)
        {
            SuspendedColors ??= Colors;
            SuspendedDesync ??= IgnoreDesync;
            Colors = IgnoreDesync = false;
        }
        else
        {
            Colors = SuspendedColors ?? Colors;
            IgnoreDesync = SuspendedDesync ?? IgnoreDesync;
            SuspendedColors = SuspendedDesync = null;
        }
    }
}
