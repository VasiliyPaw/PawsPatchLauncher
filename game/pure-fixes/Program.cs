using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;

[assembly: AssemblyTitle("Paw Pure Fixes for Kohan II 1.3.72")]
#if PAW_PURE_CHANNEL
#if PAW_PURE_BETA
[assembly: AssemblyVersion("1.3.72.9")]
[assembly: AssemblyFileVersion("1.3.72.9")]
#else
[assembly: AssemblyVersion("1.3.72.8")]
[assembly: AssemblyFileVersion("1.3.72.8")]
#endif
#else
[assembly: AssemblyVersion("1.3.72.2")]
[assembly: AssemblyFileVersion("1.3.72.2")]
#endif

namespace PawPureFixes
{
    internal static class Program
    {
        internal const string GameVersion = "1.3.72";
        internal const string GameHash = "1EB79BBB678668BE5A05F8C98103CD9988048490CE7C53C74C9A1D0813E9CD45";
        internal const string Features = "{\"id\":\"pure-fixes-runtime\",\"version\":\"1.3.72-pure.2\",\"gameVersion\":\"1.3.72\",\"negativeZero\":true,\"terrainInitialization\":true,\"stockSyncChecks\":true,\"colors\":false,\"bypass\":false,\"hostility\":false,\"randomMap\":false,\"randomTime\":false,\"menuVersions\":false,\"cityAssistant\":false,\"fastSaveTransfer\":false,\"changesGameFiles\":false,\"quiet\":true}";
        internal static string RuntimeFeatures
        {
            get
            {
#if PAW_MENU_ONLY
                return "{\"id\":\"menu-runtime\",\"version\":\"1.3.72-menu.2\",\"menuVersions\":true,\"negativeZero\":false,\"terrainInitialization\":false,\"stockSyncChecks\":true,\"changesGameFiles\":false}";
#elif PAW_PURE_CHANNEL
                return PureChannel.Features;
#elif PAW_MENU_PRESENTATION
                return Features.Replace("1.3.72-pure.2", "1.3.72-pure.4").Replace("\"menuVersions\":false", "\"menuVersions\":true");
#else
                return Features;
#endif
            }
        }
#if PAW_MENU_ONLY
        internal const string StatusFile = "paws_menu_1372_status.txt";
#else
        internal const string StatusFile = "paws_pure_fixes_1372_status.txt";
#endif
        internal static string Hash(string path)
        {
            using (FileStream stream = File.OpenRead(path))
            using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "");
        }
        internal static bool IsSupportedHash(string hash) { return String.Equals(hash, GameHash, StringComparison.OrdinalIgnoreCase); }
        internal static string GameDirectory(string[] args, string ownDirectory)
        {
            if (args.Length == 0) return Path.GetFullPath(ownDirectory);
            if (args.Length == 2 && args[0] == "--game-dir") return Path.GetFullPath(args[1]);
            throw new ArgumentException("Supported launch arguments: --game-dir <Kohan II directory>. Existing-process attach is not supported.");
        }
        internal static void Preflight(string root)
        {
            string game = Path.Combine(Path.GetFullPath(root), "k2.exe");
            if (!File.Exists(game)) throw new FileNotFoundException("Missing k2.exe.", game);
            // This executable has no FileVersion resource. Its exact known hash
            // identifies the supported 1.3.72 build; do not trust a user-editable
            // data-file version string or an absent PE version resource instead.
            if (!IsSupportedHash(Hash(game)))
                throw new InvalidDataException("Pure fixes require the supported Kohan II " + GameVersion + " executable. Select file-only fixes for this game version.");
        }
        internal static bool TrySnapshot(Func<string> readPath, Func<IntPtr> readBase, out string path, out IntPtr image)
        {
            path = null; image = IntPtr.Zero;
            try
            {
                string value = readPath(); IntPtr address = readBase();
                if (String.IsNullOrWhiteSpace(value) || address == IntPtr.Zero) return false;
                path = Path.GetFullPath(value); image = address; return true;
            }
            catch (NullReferenceException) { return false; }
        }
        internal static bool IsFreshIdentity(string expectedPath, DateTime requestedAt, string actualPath, DateTime startedAt)
        {
            return startedAt >= requestedAt && String.Equals(Path.GetFullPath(expectedPath), Path.GetFullPath(actualPath), StringComparison.OrdinalIgnoreCase);
        }
        private static Process WaitForFreshGame(string expectedPath, DateTime launch, out IntPtr image, out DateTime started)
        {
            image = IntPtr.Zero; started = default(DateTime);
            Stopwatch timer = Stopwatch.StartNew();
            while (timer.ElapsedMilliseconds < 60000)
            {
                Process[] games = Process.GetProcessesByName("k2");
                if (games.Length > 1)
                {
                    foreach (Process item in games) item.Dispose();
                    throw new InvalidOperationException("More than one Kohan II process is running.");
                }
                foreach (Process game in games)
                {
                    bool keep = false;
                    try
                    {
                        if (game.HasExited) continue;
                        DateTime time = game.StartTime.ToUniversalTime();
                        if (time < launch) throw new InvalidOperationException("An existing game process cannot be patched.");
                        game.Refresh();
                        if (game.MainWindowHandle == IntPtr.Zero) continue;
                        ProcessModule module = game.MainModule;
                        if (module == null) continue;
                        string path; IntPtr address;
                        if (!TrySnapshot(delegate { return module.FileName; }, delegate { return module.BaseAddress; }, out path, out address)) continue;
                        if (!IsFreshIdentity(expectedPath, launch, path, time))
                            throw new InvalidOperationException("Steam started a different game installation; it will not be patched.");
                        if (game.HasExited) continue;
                        // Keep a native handle owned by this Process instance
                        // for the whole launch/cleanup lifetime.
                        if (game.Handle == IntPtr.Zero) throw new InvalidOperationException("No handle for the verified game.");
                        image = address; started = time; keep = true; return game;
                    }
                    catch (Win32Exception error)
                    {
                        if (error.NativeErrorCode == 5 || !game.HasExited) throw;
                    }
                    finally { if (!keep) game.Dispose(); }
                }
                Thread.Sleep(50);
            }
            throw new TimeoutException("Steam did not create a verifiable game process within 60 seconds.");
        }
        private static void WaitForCode(NativeMemory memory, uint image, Process game)
        {
            Stopwatch timer = Stopwatch.StartNew();
            while (timer.ElapsedMilliseconds < 60000)
            {
                if (game.HasExited) throw new InvalidOperationException("The game exited before pure fixes could be installed.");
                try
                {
#if PAW_PURE_CHANNEL
                    if (PureChannel.IsReady(memory, image)) return;
#else
                    if (PurePatch.IsReady(memory, image)) return;
#endif
                }
                catch (Win32Exception error)
                {
                    if (error.NativeErrorCode != 299) throw; // Only partial-copy during decrypt is transient.
                }
                Thread.Sleep(25);
            }
            throw new InvalidDataException("Expected 1.3.72 game-code signatures did not appear. No unchecked patch was applied.");
        }
        private static void Log(string path, string text)
        {
            File.AppendAllText(path, DateTime.UtcNow.ToString("O") + " " + text + Environment.NewLine);
        }
        [STAThread]
        private static int Main(string[] args)
        {
            // Read-only tooling branches exit before any process enumeration,
            // launch, native-memory access, log changes or UI creation.
            if (args.Length == 1 && args[0] == "--features")
            {
                Console.WriteLine(RuntimeFeatures);
                return 0;
            }
            if (args.Length == 2 && args[0] == "--preflight")
            {
                try { Preflight(args[1]); Console.WriteLine("PURE_PREFLIGHT_PASS " + GameVersion); return 0; }
                catch (Exception error) { Console.Error.WriteLine(error.Message); return 2; }
            }
            string root;
            try { root = GameDirectory(args, AppDomain.CurrentDomain.BaseDirectory); }
            catch (Exception error) { Console.Error.WriteLine(error.Message); return 2; }
            string gamePath = Path.Combine(root, "k2.exe"), log = Path.Combine(root, StatusFile);
            Process game = null; DateTime verifiedStart = default(DateTime); bool complete = false;
#if PAW_PURE_SYNC
            uint syncCounter = 0, observedSync = 0;
#endif
            try
            {
                Preflight(root);
                Process[] running = Process.GetProcessesByName("k2");
                try { if (running.Length != 0) throw new InvalidOperationException("Close the existing Kohan II before starting pure fixes."); }
                finally { foreach (Process item in running) item.Dispose(); }
                Log(log, "RUNTIME_START " + RuntimeFeatures);
                DateTime launch = DateTime.UtcNow; IntPtr image;
                using (Process initial = Process.Start(new ProcessStartInfo(gamePath) { WorkingDirectory = root, UseShellExecute = true }))
                {
                    if (initial == null) throw new InvalidOperationException("Cannot start k2.exe.");
                    game = WaitForFreshGame(gamePath, launch, out image, out verifiedStart);
                }
                Preflight(root); // Recheck the path-verified image's disk identity.
#if !PAW_MENU_ONLY
                using (NativeMemory memory = new NativeMemory(game.Id, gamePath, verifiedStart))
                {
                    uint address = unchecked((uint)image.ToInt32());
                    WaitForCode(memory, address, game);
                    memory.Suspend();
                    uint cave;
                    try
                    {
#if PAW_PURE_SYNC
                        PureSync.Validate(memory, address);
#endif
#if PAW_PURE_CHANNEL
                        PureChannel.Installed installed = PureChannel.Install(memory, address);
                        cave = installed.PureCave;
#if PAW_PURE_FAST_TRANSFER
                        Log(log, "FAST_TRANSFER_R2_READY pid=" + game.Id + "; cave=0x" + installed.TransferCave.ToString("X8") +
                            "; liveCodeGuards=" + PawFastTransfer.Guards().Count + "; liveSettings=20/64/256; fileBudgetBytes=1200; maxPacketsPerPeerPerPass=16; stopBurstWhenDrained=true; receiveAckPerPass=1; stockBandwidthLimits=true; nativeProtocol=true; diskExeUnchanged=true");
#endif
#else
                        cave = PurePatch.Install(memory, address);
#endif
#if PAW_PURE_COLORS
                        PawLobbyColorsNative.Install(game.Handle, image, log);
#endif
#if PAW_PURE_SYNC
                        syncCounter = PureSync.Install(memory, address);
                        Log(log, "SYNC_PATCH_APPLIED signal=0x" + syncCounter.ToString("X8") + "; notifications=false; logOnly=true; gameContinues=true");
#endif
                    }
                    finally { memory.Resume(); }
                    Log(log, "PURE_PATCH_APPLIED pid=" + game.Id + " image=0x" + address.ToString("X8") + " cave=0x" + cave.ToString("X8") + " hooks=2 negativeZero=display-only terrainRadiusBits=BF800000");
                }
#endif
#if PAW_MENU_PRESENTATION
                PawGamePresentation.InstallMenuOnly(game.Handle, image, log, root);
#endif
                complete = true;
                // Keep the launcher-owned helper alive for game observation.
                while (!game.WaitForExit(1000))
                {
#if PAW_PURE_SYNC
                    try
                    {
                    using (var monitor = new NativeMemory(game.Id, gamePath, verifiedStart))
                    {
                        uint current = BitConverter.ToUInt32(monitor.Read(syncCounter, 4), 0);
                        if (current != observedSync)
                        {
                            Log(log, "SYNC_IGNORED count=" + current + "; previous=" + observedSync);
                            observedSync = current;
                        }
                    }
                    }
                    catch (Exception) { if (!game.HasExited) throw; }
#endif
                }
                Log(log, "PURE_GAME_EXIT exitCode=" + game.ExitCode);
                return 0;
            }
            catch (Exception error)
            {
                // Never discover or terminate another process in the failure path.
                if (!complete && game != null)
                {
                    try
                    {
                        if (!game.HasExited && game.StartTime.ToUniversalTime() == verifiedStart)
                        {
                            game.Kill();
                            if (!game.WaitForExit(5000)) throw new InvalidOperationException("Incomplete launch did not stop.");
                            Log(log, "PURE_INCOMPLETE_FRESH_LAUNCH_STOPPED pid=" + game.Id);
                        }
                    }
                    catch (Exception stopError) { try { Log(log, "PURE_STOP_ERROR " + stopError.Message); } catch { } }
                }
                try { Log(log, "PURE_START_FAILED " + error); } catch { }
                Console.Error.WriteLine(error.Message);
                return 1;
            }
            finally { if (game != null) game.Dispose(); }
        }
    }
}
