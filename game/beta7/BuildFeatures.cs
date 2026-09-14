using System;

internal static class BuildFeatures
{
    internal static int Write()
    {
#if PAW_CORELESS
        const bool commonFixes = false;
#else
        const bool commonFixes = true;
#endif
#if PAW_COLORS
        const bool colors = true;
#else
        const bool colors = false;
#endif
#if CITY_ASSISTANT
        const bool cityAssistant = true;
#else
        const bool cityAssistant = false;
#endif
#if FAST_SAVE_TRANSFER
        const bool fastSaveTransfer = true;
#else
        const bool fastSaveTransfer = false;
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
            ",\"commonFixes\":" + commonFixes.ToString().ToLowerInvariant() + ",\"quiet\":true,\"cityAssistant\":" + cityAssistant.ToString().ToLowerInvariant() +
            ",\"advancedCityPolicy\":" + (cityAssistant && fastSaveTransfer).ToString().ToLowerInvariant() +
            ",\"cityPolicyRevision\":" + (cityAssistant ? "14" : "0") +
            ",\"nativeCityQueue\":" + cityAssistant.ToString().ToLowerInvariant() +
            ",\"automaticMines\":" + cityAssistant.ToString().ToLowerInvariant() +
            ",\"newCityMilitia\":" + cityAssistant.ToString().ToLowerInvariant() +
            ",\"fastSaveTransfer\":" + fastSaveTransfer.ToString().ToLowerInvariant() + "}");
        return 0;
    }
}
