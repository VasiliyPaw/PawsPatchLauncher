param([switch]$LocalTestsOnly)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$workspace = Join-Path $repo 'release_workspace_20260905'
$publisher = Join-Path $repo 'tools\PawsPatchPublisher\bin\Release\net8.0-windows\PawsPatchPublisher.exe'
$privateKey = Join-Path $repo '.local\signing\pawpatch-signing-private.pem'
$publicKey = Join-Path $repo '.local\signing\pawpatch-signing-public.pem'
if (-not $LocalTestsOnly) {
    $oldEnvelope = (& git -C $repo show 'a3fa522:feed/beta.json') -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'Could not recover the original signed Beta release.' }
    $historyPath = Join-Path $repo 'feed\history\beta-colors-beta2.json'
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($historyPath)) | Out-Null
    [IO.File]::WriteAllText($historyPath, $oldEnvelope, [Text.UTF8Encoding]::new($false))
    & $publisher verify $historyPath $publicKey
    if ($LASTEXITCODE -ne 0) { throw 'Historical Beta signature is invalid.' }
    $betaPath = Join-Path $workspace 'feed\beta.production.payload.json'
    $beta = Get-Content -LiteralPath $betaPath -Raw | ConvertFrom-Json
    $beta | Add-Member -NotePropertyName previousReleases -NotePropertyValue @([ordered]@{
        label = 'Beta: colors beta.2'
        url = 'https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-colors-beta2.json'
    }) -Force
    $beta | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $betaPath -Encoding utf8NoBOM
}
foreach ($channel in @('stable','beta')) {
    $envelope = Get-Content -LiteralPath (Join-Path $repo "feed\$channel.json") -Raw | ConvertFrom-Json
    $payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($envelope.payload)) | ConvertFrom-Json
    foreach ($package in $payload.packages) {
        $archiveName = [IO.Path]::GetFileName(([Uri]$package.urls[0]).AbsolutePath)
        $local = Join-Path (Join-Path $workspace 'packages') $archiveName
        if (-not (Test-Path -LiteralPath $local)) { $local = Join-Path (Join-Path $repo 'packages') $archiveName }
        if (-not (Test-Path -LiteralPath $local)) { throw "Missing local test archive: $archiveName" }
        if ((Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash -ne $package.sha256) { throw "Wrong local archive: $archiveName" }
        $package.urls = @($local)
    }
    $localPayload = Join-Path $workspace "feed\$channel.reliability-test.payload.json"
    $localSigned = Join-Path $workspace "feed\$channel.reliability-test.signed.json"
    $payload | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $localPayload -Encoding utf8NoBOM
    & $publisher sign $localPayload $privateKey 'pawpatch-prod-2026' $localSigned
    if ($LASTEXITCODE -ne 0) { throw 'Could not sign local validation feed.' }
}
