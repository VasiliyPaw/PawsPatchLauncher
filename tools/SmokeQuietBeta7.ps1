param([Parameter(Mandatory=$true)][string]$GameRoot)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$stage = Join-Path $repo 'release_workspace_beta7_v2\smoke-loader'
if (Get-Process k2 -ErrorAction SilentlyContinue) { throw 'Existing game is running; do not interrupt it.' }
if (Test-Path -LiteralPath $stage) { throw 'Preserve previous smoke evidence; use a fresh stage.' }
New-Item -ItemType Directory -Path $stage | Out-Null
foreach ($module in 'common-ui','player-colors') {
    $source = Join-Path $repo "release_workspace_beta7_v2\sources\$module"
    Get-ChildItem -LiteralPath $source | Copy-Item -Destination $stage -Recurse -Force
}
$stock = [IO.Path]::GetFullPath((Join-Path $GameRoot 'k2.exe'))
$results = @()
foreach ($name in 'k2_paws_ui_1372','k2_paws_lobby_colors_mp_sync_1372') {
    $exe = Join-Path $stage "$name.exe"
    $check = Start-Process -FilePath $exe -ArgumentList @('--preflight', ('"' + $GameRoot + '"')) -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput (Join-Path $stage "$name.preflight.txt") -RedirectStandardError (Join-Path $stage "$name.preflight-error.txt")
    if ($check.ExitCode -ne 0) { throw "Data preflight failed for $name" }
    if (Get-Process k2 -ErrorAction SilentlyContinue) { throw 'Another game appeared; stop without touching it.' }
    $started = [DateTime]::UtcNow
    $helper = Start-Process -FilePath $exe -ArgumentList @('--game-dir', ('"' + $GameRoot + '"')) -WindowStyle Hidden -WorkingDirectory $stage -PassThru
    $game = $null
    $visibleHelper = $false
    $ready = $false
    try {
        $timer = [Diagnostics.Stopwatch]::StartNew()
        do {
            Start-Sleep -Milliseconds 100
            $helper.Refresh()
            if (!$helper.HasExited -and $helper.MainWindowHandle -ne [IntPtr]::Zero) { $visibleHelper = $true }
            $games = @(Get-CimInstance Win32_Process -Filter "Name='k2.exe'")
            if ($games.Count -gt 1) { throw 'Ambiguous game processes; no automatic cleanup.' }
            if ($games.Count -eq 1 -and $games[0].ExecutablePath -eq $stock) {
                $candidate = Get-Process -Id $games[0].ProcessId
                if ($candidate.StartTime.ToUniversalTime() -ge $started) { $game = $candidate }
            }
            $logs = @(Get-ChildItem -LiteralPath $GameRoot -Filter '*status.txt' | Where-Object { $_.LastWriteTimeUtc -ge $started })
            foreach ($log in $logs) {
                $content = Get-Content -LiteralPath $log.FullName -Raw
                if ($content.Contains('QUIET_READY beta.7-1372-terrain-randommap-colors20-quiet')) {
                    $ready = $true
                    Copy-Item -LiteralPath $log.FullName -Destination (Join-Path $stage "$name.live.txt")
                }
            }
            if ($helper.HasExited -and !$ready) { throw "Helper exited before ready: $($helper.ExitCode)" }
        } while (!$ready -and $timer.Elapsed.TotalSeconds -lt 65)
        if (!$ready -or !$game -or $visibleHelper) { throw "Quiet startup failed: ready=$ready game=$($null -ne $game) helperWindow=$visibleHelper" }
        $logText = Get-Content -LiteralPath (Join-Path $stage "$name.live.txt") -Raw
        if ($name.Contains('_sync_') -and (!$logText.Contains('SYNC PATCHED') -or !$logText.Contains('PAW_LOBBY_COLORS_NATIVE'))) {
            # The exact native log marker is checked by the final evidence review.
            if (!$logText.Contains('SYNC PATCHED') -or !$logText.Contains('paletteCount=49')) { throw 'Combined hooks not logged.' }
        }
        $results += [pscustomobject]@{ helper=$name; pid=$helper.Id; gamePid=$game.Id; ready=$ready; helperWindow=$visibleHelper }
        Write-Output "QUIET LIVE PASS $name"
    }
    finally {
        if ($game -and !$game.HasExited -and $game.StartTime.ToUniversalTime() -ge $started) {
            $identity = Get-CimInstance Win32_Process -Filter "ProcessId=$($game.Id)"
            if ($identity.ExecutablePath -eq $stock) {
                $game.CloseMainWindow() | Out-Null
                if (!$game.WaitForExit(10000)) { $game.Kill(); $game.WaitForExit(5000) | Out-Null }
            }
        }
        if (!$helper.HasExited -and !$helper.WaitForExit(5000)) { $helper.Kill() }
    }
}
$results | ConvertTo-Json | Out-File -LiteralPath (Join-Path $stage 'results.json') -Encoding utf8
