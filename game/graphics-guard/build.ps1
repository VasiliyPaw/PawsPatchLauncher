param(
    [Parameter(Mandatory=$true)][string]$Compiler,
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$Output
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$Output=(Resolve-Path -LiteralPath $Output).Path
$dll=Join-Path $Output 'd3d9.dll'
& $Compiler -shared -Wall -Werror (Join-Path $PSScriptRoot 'graphics_guard.c') -o $dll -lkernel32 -luser32
if($LASTEXITCODE -ne 0){throw 'DLL compilation failed'}
& $Python (Join-Path $PSScriptRoot 'prepare_guard_exports.py') $dll
if($LASTEXITCODE -ne 0){throw 'Export verification failed'}
foreach($name in @('test_graphics_guard','test_graphics_guard_d3d')) {
    $exe=Join-Path $Output ($name+'.exe')
    & $Compiler -Wall -Werror (Join-Path $PSScriptRoot ($name+'.c')) -o $exe -lkernel32 -luser32
    if($LASTEXITCODE -ne 0){throw 'Test compilation failed'}
    # The second test creates its own hidden D3D window. Never starts the game.
    & $exe $dll
    if($LASTEXITCODE -ne 0){throw ('Guard test failed: '+$name)}
}
