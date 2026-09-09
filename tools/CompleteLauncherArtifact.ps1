param(
    [Parameter(Mandatory)][string]$BuildDirectory,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [Parameter(Mandatory)][ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-fA-F]{40}$')][string]$SourceCommit,
    [Parameter(Mandatory)][bool]$RequireSignature,
    [string]$SignedDirectory,
    [string]$ExpectedPublisher
)
$ErrorActionPreference = 'Stop'
$build = (Resolve-Path -LiteralPath $BuildDirectory).Path
$output = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) { throw 'Use a new distribution directory.' }
$source = Join-Path $build 'PawsPatchLauncher.exe'
if ($RequireSignature) {
    if ([string]::IsNullOrWhiteSpace($SignedDirectory) -or [string]::IsNullOrWhiteSpace($ExpectedPublisher)) {
        throw 'SignedDirectory and ExpectedPublisher are required for a signed release.'
    }
    $source = Join-Path (Resolve-Path -LiteralPath $SignedDirectory).Path 'PawsPatchLauncher.exe'
}
$executable = Get-Item -LiteralPath $source
if ($executable.VersionInfo.FileVersion -cne "$Version.0" -or
    $executable.VersionInfo.ProductName -cne 'PawsPatchLauncher' -or
    $executable.VersionInfo.ProductVersion -cne $Version) {
    throw 'Launcher product/version metadata does not match the requested release.'
}
$signature = Get-AuthenticodeSignature -LiteralPath $source
if ($RequireSignature) {
    if ($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate) {
        throw "A valid Authenticode signature is required; status: $($signature.Status)."
    }
    if ($signature.SignerCertificate.Subject -cne $ExpectedPublisher) {
        throw 'Authenticode publisher does not match the configured signing identity.'
    }
    if ($null -eq $signature.TimeStamperCertificate) { throw 'The release signature must include a trusted timestamp.' }
} elseif ($signature.Status -ne 'NotSigned') {
    throw 'Unsigned mode expects an unsigned build. Use signed mode to validate a signed artifact.'
}
# Validate everything before producing a distributable directory.
$config = Join-Path $build 'launcher.config.json'
$null = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $output | Out-Null
Copy-Item -LiteralPath $source -Destination (Join-Path $output 'PawsPatchLauncher.exe')
Copy-Item -LiteralPath $config -Destination (Join-Path $output 'launcher.config.json')
$finalExecutable = Join-Path $output 'PawsPatchLauncher.exe'
$archive = Join-Path $output "PawsPatchLauncher-v$Version-win-x64.zip"
Compress-Archive -LiteralPath $finalExecutable,(Join-Path $output 'launcher.config.json') -DestinationPath $archive
$manifest = [ordered]@{
    version = $Version
    sourceCommit = $SourceCommit
    authenticodeRequired = $RequireSignature
    authenticodeStatus = $signature.Status.ToString()
    publisher = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { $null }
    certificateThumbprint = if ($signature.SignerCertificate) { $signature.SignerCertificate.Thumbprint } else { $null }
    timestamped = ($null -ne $signature.TimeStamperCertificate)
    files = @($finalExecutable, $archive, (Join-Path $output 'launcher.config.json')) | ForEach-Object {
        [ordered]@{ name = [IO.Path]::GetFileName($_); size = (Get-Item -LiteralPath $_).Length; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash }
    }
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $output 'launcher-artifact.json') -Encoding utf8NoBOM
Write-Output "PACKAGED $Version; Authenticode=$($signature.Status); SHA256=$((Get-FileHash -LiteralPath $finalExecutable).Hash)"
