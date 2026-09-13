using System.Diagnostics;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

namespace PawsPatchLauncher;

public static class SystemDiagnostics
{
    // Local, read-only queries with explicit property lists. No serial numbers, user names,
    // IP/MAC addresses, installed-program inventories, tokens or process command lines.
    private const string HardwareScript = """
        $ErrorActionPreference = 'Stop'
        $result = [ordered]@{}
        function Read-Hardware($label, $class, $properties) {
            try { $result[$label] = @(Get-CimInstance -ClassName $class | Select-Object -Property $properties) }
            catch { $result[$label] = @{ status = 'unavailable'; error = $_.Exception.GetType().Name } }
        }
        Read-Hardware 'os' 'Win32_OperatingSystem' @('Caption','Version','BuildNumber','OSArchitecture','TotalVisibleMemorySize','FreePhysicalMemory')
        Read-Hardware 'cpu' 'Win32_Processor' @('Name','NumberOfCores','NumberOfLogicalProcessors','MaxClockSpeed')
        Read-Hardware 'gpu' 'Win32_VideoController' @('Name','DriverVersion','DriverDate','VideoProcessor','CurrentHorizontalResolution','CurrentVerticalResolution','CurrentRefreshRate','Status')
        [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
        $result | ConvertTo-Json -Depth 5 -Compress
        """;

    public static async Task<string> CollectAsync(string? gameRoot, CancellationToken cancellationToken = default)
    {
        var report = new Dictionary<string, object?> {
            ["createdUtc"] = DateTimeOffset.UtcNow.ToString("O"),
            ["osDescription"] = RuntimeInformation.OSDescription, ["osArchitecture"] = RuntimeInformation.OSArchitecture.ToString(),
            ["processArchitecture"] = RuntimeInformation.ProcessArchitecture.ToString(), ["runtime"] = RuntimeInformation.FrameworkDescription,
            ["logicalProcessors"] = Environment.ProcessorCount, ["networkAvailable"] = NetworkInterface.GetIsNetworkAvailable(),
            ["launcherVersion"] = typeof(SystemDiagnostics).Assembly.GetName().Version?.ToString(),
            ["localTest"] = ActivityStore.LocalTestProfile is not null,
            ["timeZone"] = TimeZoneInfo.Local.Id
        };
        var disks = new List<Dictionary<string, object?>>();
        foreach (var root in new[] { gameRoot, AppContext.BaseDirectory, Path.GetTempPath() }.Where(p => !string.IsNullOrEmpty(p))
            .Select(p => Path.GetPathRoot(Path.GetFullPath(p!))).Distinct(StringComparer.OrdinalIgnoreCase))
        {
            try
            {
                var drive = new DriveInfo(root!);
                disks.Add(new() { ["drive"] = drive.Name, ["format"] = drive.DriveFormat, ["freeBytes"] = drive.AvailableFreeSpace, ["totalBytes"] = drive.TotalSize });
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException) { disks.Add(new() { ["status"] = "unavailable" }); }
        }
        report["disks"] = disks;
        try
        {
            var processes = Process.GetProcessesByName("steam");
            report["steamRunning"] = processes.Length > 0;
            foreach (var process in processes) process.Dispose();
        }
        catch { report["steamRunning"] = "unknown"; }
        try
        {
            var start = new ProcessStartInfo {
                FileName = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), @"WindowsPowerShell\v1.0\powershell.exe"),
                UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden,
                RedirectStandardOutput = true, RedirectStandardError = true, StandardOutputEncoding = Encoding.UTF8
            };
            foreach (var argument in new[] { "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", Convert.ToBase64String(Encoding.Unicode.GetBytes(HardwareScript)) }) start.ArgumentList.Add(argument);
            using var process = Process.Start(start) ?? throw new IOException("System query unavailable.");
            var output = process.StandardOutput.ReadToEndAsync(cancellationToken);
            var errors = process.StandardError.ReadToEndAsync(cancellationToken);
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(12));
            try { await process.WaitForExitAsync(timeout.Token); }
            catch (OperationCanceledException) { try { process.Kill(entireProcessTree: true); } catch { } throw; }
            var json = await output; await errors;
            if (process.ExitCode != 0 || json.Length > 128 * 1024) throw new IOException("System query failed.");
            report["hardware"] = JsonSerializer.Deserialize<JsonElement>(json);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { report["hardwareStatus"] = "query-timed-out"; }
        catch (Exception error) when (error is not OperationCanceledException) { report["hardwareStatus"] = "unavailable:" + error.GetType().Name; }
        return JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
    }
}
