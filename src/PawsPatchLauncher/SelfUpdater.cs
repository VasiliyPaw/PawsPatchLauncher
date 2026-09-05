using System.Diagnostics;
using System.Reflection;
using System.Text;

namespace PawsPatchLauncher;

public static class SelfUpdater
{
    public static Version CurrentVersion
        => Assembly.GetExecutingAssembly().GetName().Version ?? new Version(0, 0, 0);

    public static bool IsNewer(string candidate)
        => Version.TryParse(candidate, out var parsed) && parsed > CurrentVersion;

    public static bool IsBlocked(string hash) => File.Exists(BlockedPath) && File.ReadAllText(BlockedPath).Trim().Equals(hash, StringComparison.OrdinalIgnoreCase);
    public static string BlockedPath => Path.Combine(ActivityStore.Root, "failed-launcher-sha256.txt");

    public static void AcknowledgeStartup()
    {
        var args = Environment.GetCommandLineArgs();
        var index = Array.IndexOf(args, "--update-health");
        if (index < 0 || index + 1 >= args.Length || !Guid.TryParseExact(args[index + 1], "N", out _)) return;
        var token = args[index + 1];
        File.WriteAllText(Path.Combine(AppContext.BaseDirectory, ".paw-update-" + token + ".ok"), token);
    }

    public static void ScheduleReplacement(string downloadedExecutable, string hash)
    {
        var current = Environment.ProcessPath ?? throw new InvalidOperationException("The launcher executable path is unavailable.");
        if (!File.Exists(downloadedExecutable)) throw new FileNotFoundException("The downloaded launcher is missing.", downloadedExecutable);
        var currentDirectory = Path.GetDirectoryName(current) ?? throw new InvalidOperationException("The launcher directory is unavailable.");
        var staged = Path.Combine(currentDirectory, Path.GetFileName(current) + ".new");
        File.Copy(downloadedExecutable, staged, true);

        Directory.CreateDirectory(ActivityStore.Root);
        var script = BuildScript(current, staged, Environment.ProcessId, hash, ActivityStore.Root, Guid.NewGuid().ToString("N"));
        var start = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
        start.ArgumentList.Add("-NoProfile");
        start.ArgumentList.Add("-NonInteractive");
        start.ArgumentList.Add("-EncodedCommand");
        start.ArgumentList.Add(Convert.ToBase64String(Encoding.Unicode.GetBytes(script)));
        _ = Process.Start(start) ?? throw new IOException("Cannot start the update recovery helper.");
    }

    public static string BuildScript(string current, string staged, int pid, string hash, string logRoot, string token, int timeoutSeconds = 60)
    {
        static string Q(string value) => "'" + value.Replace("'", "''") + "'";
        return $$"""
        $ErrorActionPreference = 'Stop'
        $target = {{Q(current)}}
        $staged = {{Q(staged)}}
        $folder = [IO.Path]::GetDirectoryName($target)
        $backup = $target + '.previous'
        $failed = $target + '.failed'
        $ack = [IO.Path]::Combine($folder, '.paw-update-{{token}}.ok')
        $logRoot = {{Q(logRoot)}}
        $replaced = $false
        $candidate = $null
        function Start-Launcher([string]$arguments) {
            $info = New-Object System.Diagnostics.ProcessStartInfo
            $info.FileName = $target
            $info.WorkingDirectory = $folder
            $info.Arguments = $arguments
            $info.UseShellExecute = $false
            $info.CreateNoWindow = $true
            return [Diagnostics.Process]::Start($info)
        }
        try {
            $old = $null
            try { $old = [Diagnostics.Process]::GetProcessById({{pid}}) } catch [ArgumentException] { }
            if ($null -ne $old -and -not $old.WaitForExit(60000)) { throw 'The original launcher did not exit.' }
            if ([IO.File]::Exists($ack)) { [IO.File]::Delete($ack) }
            $sha = [Security.Cryptography.SHA256]::Create()
            $stream = [IO.File]::OpenRead($staged)
            try { $actual = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') } finally { $stream.Dispose(); $sha.Dispose() }
            if ($actual -ne {{Q(hash)}}) { throw 'Staged launcher hash mismatch.' }
            if ([IO.File]::Exists($backup)) { [IO.File]::Delete($backup) }
            [IO.File]::Replace($staged, $target, $backup)
            $replaced = $true
            $candidate = Start-Launcher '--update-health {{token}}'
            $until = [DateTime]::UtcNow.AddSeconds({{timeoutSeconds}})
            $healthy = $false
            while ([DateTime]::UtcNow -lt $until) {
                $candidate.Refresh()
                if ($candidate.HasExited) { break }
                if ([IO.File]::Exists($ack) -and [IO.File]::ReadAllText($ack) -eq '{{token}}') { $healthy = $true; break }
                [Threading.Thread]::Sleep(250)
            }
            if (-not $healthy) { throw 'The new launcher did not confirm a working window.' }
            [IO.File]::Delete($ack)
            [IO.File]::WriteAllText([IO.Path]::Combine($logRoot, 'self-update.log'), 'Update confirmed: ' + {{Q(hash)}})
        } catch {
            [void][IO.Directory]::CreateDirectory($logRoot)
            [IO.File]::WriteAllText([IO.Path]::Combine($logRoot, 'self-update.log'), $_.ToString())
            if ($replaced) {
                if ($null -ne $candidate -and -not $candidate.HasExited) { $candidate.Kill(); $candidate.WaitForExit() }
                if ([IO.File]::Exists($failed)) { [IO.File]::Delete($failed) }
                [IO.File]::Replace($backup, $target, $failed)
                [IO.File]::WriteAllText([IO.Path]::Combine($logRoot, 'failed-launcher-sha256.txt'), {{Q(hash)}})
                [IO.File]::WriteAllText([IO.Path]::Combine($logRoot, 'update-rollback.txt'), 'The launcher update failed. The previous executable was restored.')
                [void](Start-Launcher '')
            }
        }
        """;
    }
}
