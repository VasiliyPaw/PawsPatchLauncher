param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$out=[IO.Path]::GetFullPath($OutputDirectory)
[IO.Directory]::CreateDirectory($out) | Out-Null
$csc=Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
$refs=@('/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.Core.dll','/r:System.IO.Compression.FileSystem.dll','/r:System.IO.Compression.dll')
$sources=@((Join-Path $PSScriptRoot 'LairReader.cs'),(Join-Path $PSScriptRoot 'Program.cs'),(Join-Path $PSScriptRoot 'GameAttachment.cs'))
& $csc /nologo /target:winexe /platform:x86 /optimize+ /utf8output "/out:$out\PawsLairDiagnostics.exe" @refs @sources
if($LASTEXITCODE -ne 0){throw 'Diagnostic compilation failed.'}
& $csc /nologo /target:exe /platform:x86 /optimize+ /utf8output /main:PawLairDiagnostics.LairReaderTests "/out:$out\LairReaderTests.exe" @refs @sources (Join-Path $PSScriptRoot 'LairReaderTests.cs')
if($LASTEXITCODE -ne 0){throw 'Diagnostic tests compilation failed.'}
& "$out\LairReaderTests.exe"
if($LASTEXITCODE -ne 0){throw 'Diagnostic tests failed.'}
Get-FileHash -LiteralPath "$out\PawsLairDiagnostics.exe" -Algorithm SHA256
