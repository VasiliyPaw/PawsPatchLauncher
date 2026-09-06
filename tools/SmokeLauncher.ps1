param([string]$BuildDirectory = (Join-Path $PSScriptRoot '..\artifacts\win-x64'))
$ErrorActionPreference = 'Stop'
# Process-local and inherited by the two test children, including older EXEs and
# failures before managed startup. No registry, WER service or user's process changes.
if (-not ('PawsSmokeNative.ErrorMode' -as [type])) {
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
namespace PawsSmokeNative {
    public static class ErrorMode {
        [DllImport("kernel32.dll", ExactSpelling=true)] public static extern uint GetErrorMode();
        [DllImport("kernel32.dll", ExactSpelling=true)] public static extern uint SetErrorMode(uint mode);
    }
}
'@
}
$previousTestErrorMode = [PawsSmokeNative.ErrorMode]::GetErrorMode()
$null = [PawsSmokeNative.ErrorMode]::SetErrorMode($previousTestErrorMode -bor 3)
try {
$build = [IO.Path]::GetFullPath($BuildDirectory)
$exe = Join-Path $build 'PawsPatchLauncher.exe'
if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Missing published launcher: $exe" }
$standalone = Join-Path (Split-Path $build) ('standalone-smoke-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $standalone | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $standalone 'PawsPatchLauncher.exe')
foreach ($directory in @($build, $standalone)) {
    $runLogs = Join-Path ([IO.Path]::GetTempPath()) ('PawsSmokeRuns\' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $runLogs | Out-Null
    # Redirection uses direct process creation, so the parent's error mode is inherited.
    $process = Start-Process -FilePath (Join-Path $directory 'PawsPatchLauncher.exe') -WorkingDirectory $directory -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runLogs 'stdout.log') -RedirectStandardError (Join-Path $runLogs 'stderr.log')
    $marker = Join-Path ([IO.Path]::GetTempPath()) "PawsPatchLauncherSmoke\$($process.Id)\window-ready.txt"
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        while (!(Test-Path -LiteralPath $marker) -and !$process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Milliseconds 200
            $process.Refresh()
        }
        if (!(Test-Path -LiteralPath $marker)) {
            $failureCode = if ($process.HasExited) { $process.ExitCode } else { 'still running' }
            throw "Launcher did not acknowledge its window: $directory; exit=$failureCode; logs=$(Split-Path $marker); console=$runLogs"
        }
        Start-Sleep -Seconds 2
        $process.Refresh()
        if ($process.HasExited) { throw "Launcher exited after window acknowledgement: $($process.ExitCode)" }
        if (Test-Path -LiteralPath (Join-Path (Split-Path $marker) 'launcher-errors.log')) { throw "Launcher logged an exception: $marker" }
        Write-Output "SMOKE PASS pid=$($process.Id) window=$($process.MainWindowHandle) directory=$directory"
    } finally {
        if (!$process.HasExited) {
            $null = $process.CloseMainWindow()
            if (!$process.WaitForExit(5000)) { $process.Kill(); $process.WaitForExit() }
        }
        $process.Dispose()
    }
}
Get-FileHash -LiteralPath $exe -Algorithm SHA256 | Format-List
Get-Item -LiteralPath $exe | Select-Object Length, LastWriteTime
} finally {
    $null = [PawsSmokeNative.ErrorMode]::SetErrorMode($previousTestErrorMode)
}
