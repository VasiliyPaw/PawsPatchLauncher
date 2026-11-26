param([ValidateRange(20,180)][int]$Seconds=180,[ValidateRange(1,672)][int]$MaxModels=24,[ValidateSet('generate.py','generate_shard.py')][string]$WorkerScript='generate.py',[ValidateRange(-1,1)][int]$ShardIndex=-1)
$ErrorActionPreference='Stop'
$taskRoot='G:\CodexData\projects\Codex\2026-09-09\paws-patch-kohan-ii-3\work\bridge-materials-full-20261126'
$python='C:\Users\Paw\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if(($WorkerScript -eq 'generate.py' -and $ShardIndex -ne -1) -or ($WorkerScript -eq 'generate_shard.py' -and $ShardIndex -lt 0)){throw 'Worker script/shard parameters disagree'}
$workerPath=Join-Path $taskRoot $WorkerScript
$foreign=@(Get-CimInstance Win32_Process|Where-Object { $_.Name -match '^(k2\.exe|KohanReborn.*)$' })
if($foreign.Count){throw 'Foreign game present; CPU batch refused without controlling it'}
$env:TEMP="$taskRoot\temp";$env:TMP=$env:TEMP;$env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false'
$env:OPENBLAS_NUM_THREADS='1';$env:OMP_NUM_THREADS='1';$env:MKL_NUM_THREADS='1';$env:PYTHONDONTWRITEBYTECODE='1'
$batchTag=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')+'-'+$ShardIndex+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
New-Item -ItemType Directory -Force -Path "$taskRoot\logs"|Out-Null
$stdout="$taskRoot\logs\$batchTag.stdout.log";$stderr="$taskRoot\logs\$batchTag.stderr.log"
$proc=$null;$exitCode=1;$failure=$null
$receipt=@{seconds=$Seconds;maxModels=$MaxModels;priority='BelowNormal';stdout=$stdout;stderr=$stderr;noGameSdkGpu=$true}
try{
 $workerArgs=@('-B',$workerPath,'--seconds',"$Seconds",'--max-models',"$MaxModels")
 if($ShardIndex -ge 0){$workerArgs+=@('--index',"$ShardIndex")}
 $proc=Start-Process -FilePath $python -ArgumentList $workerArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
 $null=$proc.Handle
 $proc.PriorityClass=[Diagnostics.ProcessPriorityClass]::BelowNormal
 $identity=Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)"
 if(-not $identity -or $identity.ParentProcessId -ne $PID -or -not $identity.CommandLine.Contains($workerPath)){throw 'Own worker parent/command did not match'}
 $expectedImage=(Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash
 if((Get-FileHash -LiteralPath $identity.ExecutablePath -Algorithm SHA256).Hash -ne $expectedImage){throw 'Own worker executable fingerprint did not match'}
 $receipt.pid=$proc.Id;$receipt.creation=$identity.CreationDate.ToUniversalTime().ToString('o');$receipt.exe=$identity.ExecutablePath
 $receipt.workerScript=$WorkerScript;$receipt.shardIndex=$ShardIndex
 $runningName=$(if($ShardIndex -lt 0){'running-batch.json'}else{"running-shard-$ShardIndex.json"})
 $receipt|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskRoot $runningName)
 $proc.WaitForExit();$exitCode=$proc.ExitCode
}catch{$failure=$_.ToString()}
finally{
 if($proc){
  # Held Start-Process handle identifies our own child even after a guard error.
  if(-not $proc.HasExited){$proc.Kill();$proc.WaitForExit()}
  $children=@(Get-CimInstance Win32_Process|Where-Object { $_.ParentProcessId -eq $proc.Id -and $_.ExecutablePath -eq "$taskRoot\ao_trace.exe" })
  foreach($child in $children){$held=Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue;if($held){$null=$held.Handle;if(-not $held.HasExited){$held.Kill();$held.WaitForExit()}}}
 }
}
$remaining=@(Get-CimInstance Win32_Process|Where-Object { $proc -and ($_.ProcessId -eq $proc.Id -or ($_.ParentProcessId -eq $proc.Id -and $_.ExecutablePath -eq "$taskRoot\ao_trace.exe")) })
$receipt.closedUtc=[DateTime]::UtcNow.ToString('o');$receipt.exitCode=$exitCode;$receipt.failure=$failure;$receipt.remainingOwn=$remaining.Count;$receipt.allOwnedClosed=($remaining.Count -eq 0)
$closureName=$(if($ShardIndex -lt 0){'last-closure.json'}else{"closure-shard-$ShardIndex.json"})
$receipt|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskRoot $closureName)
if(Test-Path -LiteralPath $stdout){Get-Content -LiteralPath $stdout}
if((Test-Path -LiteralPath $stderr) -and (Get-Item -LiteralPath $stderr).Length){Get-Content -LiteralPath $stderr}
$receipt|ConvertTo-Json
exit $exitCode
