using System;
using System.IO;

namespace PawPureFixes
{
    // This file is included only in the scoped Vanilla/Immortals channel builds.
    // The shared R2 source supplies the exact same native code as Arcane Wars.
    internal static class PureChannel
    {
#if PAW_PURE_FAST_TRANSFER
        internal const string Channel = "beta", Version = "1.3.72-pure.7-beta.1", PatchVersion = "0.2.0-beta.1";
        internal const bool FastTransfer = true;
#else
        internal const string Channel = "stable", Version = "1.3.72-pure.6", PatchVersion = "0.1.1";
        internal const bool FastTransfer = false;
#endif
        internal static string Features
        {
            get
            {
                return Program.Features.Replace("1.3.72-pure.2", Version)
                    .Replace("\"menuVersions\":false", "\"menuVersions\":true")
                    .Replace("\"fastSaveTransfer\":false", "\"fastSaveTransfer\":" + (FastTransfer ? "true" : "false"))
                    .Replace("{", "{\"channel\":\"" + Channel + "\",\"patchVersion\":\"" + PatchVersion + "\",\"nativeTransferRevision\":\"" + (FastTransfer ? "R2" : "stock") + "\",");
            }
        }
        internal sealed class Installed
        {
            internal uint PureCave, TransferCave;
        }
        internal static bool IsReady(IPatchMemory memory, uint image)
        {
            if (!PurePatch.IsReady(memory, image)) return false;
#if PAW_PURE_FAST_TRANSFER
            try { PawFastTransfer.Validate(memory, image); }
            catch (InvalidDataException) { return false; }
#endif
            return true;
        }
        internal static Installed Install(IPatchMemory memory, uint image)
        {
            PurePatch.Validate(memory, image);
#if PAW_PURE_FAST_TRANSFER
            // Validate all R2 code and live protocol settings before either
            // feature allocates or writes to the fresh, suspended process.
            PawFastTransfer.Validate(memory, image);
#endif
            var installed = new Installed { PureCave = PurePatch.Install(memory, image) };
#if PAW_PURE_FAST_TRANSFER
            try { installed.TransferCave = PawFastTransfer.InstallCore(memory, image); }
            catch
            {
                PurePatch.Uninstall(memory, image, installed.PureCave);
                throw;
            }
#endif
            return installed;
        }
    }
}
