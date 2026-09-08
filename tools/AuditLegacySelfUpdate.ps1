param(
    [Parameter(Mandatory=$true)][string]$Baseline,
    [Parameter(Mandatory=$true)][string]$Candidate,
    [Parameter(Mandatory=$true)][string]$HostModelPath,
    [Parameter(Mandatory=$true)][string]$OutputRoot
)
$ErrorActionPreference='Stop'
# Read the verified public binary, not current source. Bundle layout reference:
# https://github.com/dotnet/runtime/blob/v8.0.0/src/installer/managed/Microsoft.NET.HostModel/Bundle/Manifest.cs
# Only disposable copies are started/replaced; every child uses --smoke-test.
$legacyBaseline=[IO.Path]::GetFullPath($Baseline)
$legacyCandidate=[IO.Path]::GetFullPath($Candidate)
$legacyRoot=[IO.Path]::GetFullPath($OutputRoot)
if(Test-Path -LiteralPath $legacyRoot){throw 'Use a new audit root.'}
if((Get-FileHash -LiteralPath $legacyBaseline).Hash -ne '19ACD915FFFFF83DF24F2BC31DF0DF6A7BA8106986B265EA6C3D0EFBA27BCED9'){throw 'Unexpected public 0.5.8 binary.'}
if((Get-FileHash -LiteralPath $legacyCandidate).Hash -ne 'CB349946EA58ED97E099386862E408B51E7E7561F015A10EC340033E15E15261'){throw 'Unexpected audited candidate.'}
$null=[Reflection.Assembly]::LoadFrom([IO.Path]::GetFullPath($HostModelPath))
[long]$legacyOffset=0
if(![Microsoft.NET.HostModel.AppHost.HostWriter]::IsBundle($legacyBaseline,[ref]$legacyOffset)){throw 'Not a bundle.'}
$legacyReader=[IO.BinaryReader]::new([IO.File]::OpenRead($legacyBaseline))
try {
    $legacyReader.BaseStream.Position=$legacyOffset
    $major=$legacyReader.ReadUInt32(); $minor=$legacyReader.ReadUInt32(); $entries=$legacyReader.ReadInt32()
    $null=$legacyReader.ReadString()
    if($major -ne 6 -or $minor -ne 0 -or $entries -gt 1000){throw 'Unexpected bundle format.'}
    $legacyReader.BaseStream.Position+=40
    $assemblyEntry=$null
    for($i=0;$i -lt $entries;$i++){
        $offset=$legacyReader.ReadInt64(); $size=$legacyReader.ReadInt64(); $compressed=$legacyReader.ReadInt64()
        $type=$legacyReader.ReadByte(); $name=$legacyReader.ReadString()
        if($name -eq 'PawsPatchLauncher.dll'){$assemblyEntry=@{Offset=$offset;Size=$size;Compressed=$compressed;Type=$type}}
    }
    if(!$assemblyEntry -or $assemblyEntry.Size -gt 20000000){throw 'Missing bounded launcher assembly.'}
    $legacyReader.BaseStream.Position=$assemblyEntry.Offset
    $length=if($assemblyEntry.Compressed -gt 0){$assemblyEntry.Compressed}else{$assemblyEntry.Size}
    $bytes=$legacyReader.ReadBytes([int]$length)
    if($bytes.Length -ne $length){throw 'Truncated bundle.'}
    if($assemblyEntry.Compressed -gt 0){
        $inputStream=[IO.MemoryStream]::new($bytes,$false); $outputStream=[IO.MemoryStream]::new()
        $inflate=[IO.Compression.DeflateStream]::new($inputStream,[IO.Compression.CompressionMode]::Decompress)
        try{$inflate.CopyTo($outputStream);$bytes=$outputStream.ToArray()}finally{$inflate.Dispose();$inputStream.Dispose();$outputStream.Dispose()}
    }
    if($bytes.Length -ne $assemblyEntry.Size){throw 'Assembly length mismatch.'}
} finally {$legacyReader.Dispose()}
$legacyAssembly=[Reflection.Assembly]::Load($bytes)
if($legacyAssembly.GetName().Version.ToString() -ne '0.5.8.0'){throw 'Unexpected assembly version.'}
$legacyBuilder=$legacyAssembly.GetType('PawsPatchLauncher.SelfUpdater',$true).GetMethod('BuildScript')
if(!$legacyBuilder -or $legacyBuilder.GetParameters().Count -ne 7){throw 'Unexpected legacy helper signature.'}
New-Item -ItemType Directory -Path $legacyRoot | Out-Null
function Close-AuditChild($process){
    $process.Refresh()
    if(!$process.HasExited){$null=$process.CloseMainWindow();if(!$process.WaitForExit(5000)){$process.Kill();$process.WaitForExit()}}
}
foreach($case in @('short','long')){
    $caseRoot=Join-Path $legacyRoot ($case+" Русский & user's [folder]")
    if($case -eq 'long'){$caseRoot=Join-Path $caseRoot ('x' * (225-$caseRoot.Length-1))}
    New-Item -ItemType Directory -Path $caseRoot | Out-Null
    $target=Join-Path $caseRoot 'Launcher.exe'
    if(!$target.StartsWith($legacyRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Target escaped fixture root.'}
    Copy-Item -LiteralPath $legacyBaseline -Destination $target
    Copy-Item -LiteralPath $legacyCandidate -Destination ($target+'.new')
    $oldInfo=[Diagnostics.ProcessStartInfo]::new($target)
    $oldInfo.WorkingDirectory=$caseRoot
    $oldInfo.UseShellExecute=$false; $oldInfo.CreateNoWindow=$true; $oldInfo.WindowStyle='Hidden'
    $oldInfo.ArgumentList.Add('--smoke-test')
    $old=[Diagnostics.Process]::Start($oldInfo)
    try {
        $ready=Join-Path ([IO.Path]::GetTempPath()) ('PawsPatchLauncherSmoke/'+$old.Id+'/window-ready.txt')
        $deadline=[DateTime]::UtcNow.AddSeconds(30)
        while(!(Test-Path -LiteralPath $ready) -and !$old.HasExited -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Milliseconds 100;$old.Refresh()}
        if(!(Test-Path -LiteralPath $ready)){throw 'Public baseline did not acknowledge smoke window.'}
        $token=[Guid]::NewGuid().ToString('N')
        $newHash=(Get-FileHash -LiteralPath $legacyCandidate).Hash
        # Only changes to generated legacy helper: isolated smoke child and a 15s test timeout.
        $script=$legacyBuilder.Invoke($null,[object[]]@([string]$target,[string]($target+'.new'),[int]$old.Id,[string]$newHash,[string]$caseRoot,[string]$token,[int]15))
        if(!$script.Contains('$info.Arguments = $arguments')){throw 'Expected smoke isolation hook missing.'}
        $script=$script.Replace('$info.Arguments = $arguments',"`$info.Arguments = `$arguments + ' --smoke-test'")
        $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
        $helper=Start-Process -FilePath powershell.exe -ArgumentList @('-NoProfile','-NonInteractive','-EncodedCommand',$encoded) -WindowStyle Hidden -PassThru
        Close-AuditChild $old
        if(!$helper.WaitForExit(45000)){throw 'Legacy helper exceeded test deadline.'}
        $resultHash=(Get-FileHash -LiteralPath $target).Hash
        $log=Get-Content -LiteralPath (Join-Path $caseRoot 'self-update.log') -Raw
        $ack=Join-Path $caseRoot ('.paw-update-'+$token+'.ok')
        $ackExists=Test-Path -LiteralPath $ack
        $ackMatches=$ackExists -and ((Get-Content -LiteralPath $ack -Raw) -eq $token)
        if($case -eq 'short' -and $resultHash -ne $newHash){throw 'Legacy short-path update failed: '+$log}
        [pscustomobject]@{Case=$case;BuilderVersion=$legacyAssembly.GetName().Version.ToString();Updated=($resultHash -eq $newHash);AckPathLength=$ack.Length;AckRemains=$ackExists;AckMatches=$ackMatches;Log=$log.Trim();Fixture=$caseRoot} | ConvertTo-Json -Compress
        $helper.Dispose()
    } finally {
        # Rollback may start another baseline copy. Never close the user's launcher.
        Get-Process Launcher -ErrorAction SilentlyContinue | ForEach-Object {
            try {if($_.Path -eq $target){Close-AuditChild $_}} finally {$_.Dispose()}
        }
        $old.Dispose()
    }
}
