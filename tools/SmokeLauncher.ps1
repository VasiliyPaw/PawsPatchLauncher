param([string]$BuildDirectory = (Join-Path $PSScriptRoot '..\artifacts\win-x64'))
$ErrorActionPreference = 'Stop'
$build = [IO.Path]::GetFullPath($BuildDirectory)
$exe = Join-Path $build 'PawsPatchLauncher.exe'
if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Missing published launcher: $exe" }
$standalone = Join-Path (Split-Path $build) ('standalone-smoke-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $standalone | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $standalone 'PawsPatchLauncher.exe')
foreach ($directory in @($build, $standalone)) {
    $process = Start-Process -FilePath (Join-Path $directory 'PawsPatchLauncher.exe') -WorkingDirectory $directory -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru
    $marker = Join-Path ([IO.Path]::GetTempPath()) "PawsPatchLauncherSmoke\$($process.Id)\window-ready.txt"
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        while (!(Test-Path -LiteralPath $marker) -and !$process.HasExited -and [DateTime]::UtcNow -lt $deadline) {
            Start-Sleep -Milliseconds 200
            $process.Refresh()
        }
        if (!(Test-Path -LiteralPath $marker)) { throw "Launcher did not acknowledge its window: $directory; exited=$($process.HasExited)" }
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
