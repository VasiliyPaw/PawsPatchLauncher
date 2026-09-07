using System;

internal static class BuildFeatures
{
    internal static int Write()
    {
#if PAW_COLORS
        const bool colors = true;
#else
        const bool colors = false;
#endif
#if SYNC_CONTINUE
        const bool bypass = true;
#else
        const bool bypass = false;
#endif
#if SYNC_ONLY
        const bool hostility = false;
#else
        const bool hostility = true;
#endif
        Console.WriteLine("{\"colors\":" + colors.ToString().ToLowerInvariant() +
            ",\"bypass\":" + bypass.ToString().ToLowerInvariant() +
            ",\"hostility\":" + hostility.ToString().ToLowerInvariant() +
            ",\"commonFixes\":true,\"quiet\":true}");
        return 0;
    }
}
