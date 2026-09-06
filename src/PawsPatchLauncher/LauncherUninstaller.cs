using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public static class LauncherUninstaller
{
    public static async Task ScheduleAsync()
    {
        var executable = Environment.ProcessPath ?? throw new IOException("Launcher path is unavailable.");
        if (!Path.GetExtension(executable).Equals(".exe", StringComparison.OrdinalIgnoreCase)
            || FileVersionInfo.GetVersionInfo(executable).ProductName != "PawsPatchLauncher")
            throw new IOException("Self-removal is available only in the standalone launcher EXE.");
        using var process = Process.GetCurrentProcess();
        var script = await BuildScriptAsync(executable, ActivityStore.Root, process.Id, process.StartTime.ToUniversalTime().Ticks);
        var start = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
        start.ArgumentList.Add("-NoProfile"); start.ArgumentList.Add("-NonInteractive");
        start.ArgumentList.Add("-EncodedCommand");
        start.ArgumentList.Add(Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
        _ = Process.Start(start) ?? throw new IOException("Cannot start the removal helper.");
    }

    // Only exact launcher/update filenames and this account's standard app-data
    // directory. Never recurse through the EXE's parent (often Desktop/Downloads),
    // the game directory, or a user-specified custom cache location.
    public static async Task<string> BuildScriptAsync(string executable, string dataRoot, int processId, long startTicks, bool showErrors = true)
    {
        executable = Path.GetFullPath(executable);
        dataRoot = Path.GetFullPath(dataRoot);
        if (Path.GetFileName(dataRoot) != "PawsPatchLauncher" || Path.GetDirectoryName(dataRoot) is null)
            throw new InvalidDataException("Unexpected launcher data directory.");
        RemovalSafety.CheckNoLinks(executable);
        RemovalSafety.CheckNoLinks(dataRoot);
        var exeHash = await CryptoAndIO.Sha256Async(executable);
        var companions = new Dictionary<string, string>();
        foreach (var suffix in new[] { ".previous", ".failed", ".new" })
        {
            var path = executable + suffix;
            RemovalSafety.CheckNoLinks(path);
            if (File.Exists(path)) companions[path] = await CryptoAndIO.Sha256Async(path);
        }
        // Paths go through JSON/Base64, never interpolated as shell syntax.
        var plan = Convert.ToBase64String(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new { executable, dataRoot, exeHash, companions })));
        return $$"""
        $ErrorActionPreference = 'Stop'
        $plan = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{{plan}}')) | ConvertFrom-Json
        function Assert-NoLinks([string]$path) {
            $current = [IO.Path]::GetFullPath($path)
            while ($null -ne $current) {
                if (([IO.File]::Exists($current) -or [IO.Directory]::Exists($current)) -and (([IO.File]::GetAttributes($current) -band [IO.FileAttributes]::ReparsePoint) -ne 0)) { throw ('Unsafe linked path: ' + $current) }
                $current = [IO.Path]::GetDirectoryName($current)
            }
        }
        function Hash([string]$path) {
            $sha = [Security.Cryptography.SHA256]::Create(); $stream = [IO.File]::OpenRead($path)
            try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') } finally { $stream.Dispose(); $sha.Dispose() }
        }
        try {
            $old = $null
            try { $old = [Diagnostics.Process]::GetProcessById({{processId}}) } catch [ArgumentException] { }
            if ($null -ne $old -and $old.StartTime.ToUniversalTime().Ticks -eq {{startTicks}}L -and -not $old.WaitForExit(60000)) { throw 'Launcher did not exit; nothing removed.' }
            $mutex = New-Object Threading.Mutex($false, 'Local\PawsPatchLauncher-Reliability')
            $locked = $false
            try { $locked = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked = $true }
            if (-not $locked) { throw 'Another launcher is running; nothing removed.' }
            Assert-NoLinks $plan.executable
            Assert-NoLinks $plan.dataRoot
            if ((Hash $plan.executable) -ne $plan.exeHash) { throw 'Launcher changed; nothing removed.' }
            foreach ($entry in $plan.companions.PSObject.Properties) {
                Assert-NoLinks $entry.Name
                if ([IO.File]::Exists($entry.Name) -and (Hash $entry.Name) -ne $entry.Value) { throw 'Update companion changed; nothing removed.' }
            }
            # Enumerate only known application-owned caches; collect/validate all
            # paths first, then delete files individually (no recursive deletion).
            $files = New-Object 'Collections.Generic.List[string]'
            $folders = New-Object 'Collections.Generic.List[string]'
            foreach ($name in @('downloads','launcher','releases')) {
                $root = [IO.Path]::Combine($plan.dataRoot, $name)
                if (-not [IO.Directory]::Exists($root)) { continue }
                $pending = New-Object 'Collections.Generic.Stack[string]'; $pending.Push($root)
                while ($pending.Count -gt 0) {
                    $dir = $pending.Pop(); Assert-NoLinks $dir; $folders.Add($dir)
                    foreach ($file in [IO.Directory]::EnumerateFiles($dir)) { Assert-NoLinks $file; $files.Add($file) }
                    foreach ($child in [IO.Directory]::EnumerateDirectories($dir)) { Assert-NoLinks $child; $pending.Push($child) }
                }
            }
            foreach ($name in @('settings.json','settings.json.tmp','game-run.json','game-run.json.tmp','launcher-run.json','launcher-run.json.tmp','launcher-errors.log','self-update.log','failed-launcher-sha256.txt','update-rollback.txt')) {
                $file = [IO.Path]::Combine($plan.dataRoot, $name); Assert-NoLinks $file
                if ([IO.File]::Exists($file)) { $files.Add($file) }
            }
            foreach ($file in $files) { Assert-NoLinks $file; [IO.File]::Delete($file) }
            foreach ($dir in ($folders | Sort-Object Length -Descending)) { if (@([IO.Directory]::EnumerateFileSystemEntries($dir)).Count -eq 0) { [IO.Directory]::Delete($dir, $false) } }
            foreach ($entry in $plan.companions.PSObject.Properties) { [IO.File]::Delete($entry.Name) }
            [IO.File]::Delete($plan.executable)
            if ([IO.Directory]::Exists($plan.dataRoot) -and @([IO.Directory]::EnumerateFileSystemEntries($plan.dataRoot)).Count -eq 0) { [IO.Directory]::Delete($plan.dataRoot, $false) }
        } catch {
            if ({{(showErrors ? "$true" : "$false")}}) {
                Add-Type -AssemblyName PresentationFramework
                [void][Windows.MessageBox]::Show($_.Exception.Message, 'Launcher uninstall / Удаление лаунчера')
            }
            exit 1
        } finally { if ($locked) { $mutex.ReleaseMutex() }; if ($null -ne $mutex) { $mutex.Dispose() } }
        """;
    }
}
