param(
    [Parameter(Mandatory)][string]$BuildDirectory,
    [Parameter(Mandatory)][string]$WorkDirectory
)
$ErrorActionPreference = 'Stop'
$build = (Resolve-Path -LiteralPath $BuildDirectory).Path
$work = [IO.Path]::GetFullPath($WorkDirectory)
if (Test-Path -LiteralPath $work) { throw 'Use a fresh test directory.' }
New-Item -ItemType Directory -Path $work | Out-Null
$exe = Join-Path $build 'PawsPatchLauncher.exe'
$version = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
$commit = '0123456789012345678901234567890123456789'
$package = Join-Path $PSScriptRoot 'CompleteLauncherArtifact.ps1'
$count = 0
function Expect-Rejection([hashtable]$Values, [string]$ExpectedMessage) {
    $rejected = $false
    try { & $package @Values } catch {
        if ($_.Exception.Message -notlike $ExpectedMessage) { throw }
        $rejected = $true
    }
    if (!$rejected) { throw "Unsafe packaging succeeded: $ExpectedMessage" }
    if (Test-Path -LiteralPath $Values.OutputDirectory) { throw 'Rejected build produced a distribution directory.' }
    $script:count++
}
$base = @{BuildDirectory=$build; Version=$version; SourceCommit=$commit; RequireSignature=$true}
Expect-Rejection ($base + @{OutputDirectory=(Join-Path $work 'missing-settings')}) '*SignedDirectory and ExpectedPublisher*'
Expect-Rejection ($base + @{OutputDirectory=(Join-Path $work 'unsigned-rejected'); SignedDirectory=$build; ExpectedPublisher='CN=SignPath Foundation'}) '*valid Authenticode signature*NotSigned*'
$wrong = $base.Clone(); $wrong.Version = '999.0.0'; $wrong.RequireSignature = $false
Expect-Rejection ($wrong + @{OutputDirectory=(Join-Path $work 'wrong-version')}) '*metadata does not match*'
$unsigned = $base.Clone(); $unsigned.RequireSignature = $false; $unsigned.OutputDirectory = Join-Path $work 'unsigned'
& $package @unsigned
$manifest = Get-Content -LiteralPath (Join-Path $unsigned.OutputDirectory 'launcher-artifact.json') -Raw | ConvertFrom-Json
if ($manifest.authenticodeRequired -or $manifest.authenticodeStatus -ne 'NotSigned' -or $manifest.publisher) { throw 'Unsigned artifact misrepresented its signature.' }
$count++
foreach ($file in $manifest.files) {
    $path = Join-Path $unsigned.OutputDirectory $file.name
    if ($file.sha256 -cne (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -or $file.size -ne (Get-Item -LiteralPath $path).Length) { throw 'Final digest/size mismatch.' }
    $count++
}
$expanded = Join-Path $work 'expanded'
Expand-Archive -LiteralPath (Join-Path $unsigned.OutputDirectory "PawsPatchLauncher-v$version-win-x64.zip") -DestinationPath $expanded
if ((Get-FileHash -LiteralPath (Join-Path $expanded 'PawsPatchLauncher.exe')).Hash -cne (Get-FileHash -LiteralPath $exe).Hash) { throw 'ZIP contains a different executable.' }
$count++
Write-Output "PASS: $count signing/packaging checks (no certificate created or installed)."
