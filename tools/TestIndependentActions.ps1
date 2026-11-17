param(
    [Parameter(Mandatory=$true)][string]$WorkDirectory,
    [string]$DotnetPath='dotnet',
    [switch]$SkipBuild
)
$ErrorActionPreference='Stop'
$taskRepo=Split-Path $PSScriptRoot -Parent
$taskRoot=[IO.Path]::GetFullPath($WorkDirectory)
$taskReports=Join-Path $taskRoot 'reports'
New-Item -ItemType Directory -Force -Path $taskReports | Out-Null
Push-Location $taskRepo
try {
    if(!$SkipBuild){
        & $DotnetPath build tools/PreviewRenderer/PreviewRenderer.csproj -c Release -p:UseSharedCompilation=false
        if($LASTEXITCODE -ne 0){throw 'Independent action fixture build failed.'}
    }
    foreach($taskLanguage in @('ru','en','uk','cs','de','fr')){
        $taskProfile=Join-Path $taskRoot ('profiles/'+$taskLanguage)
        & $DotnetPath tools/PreviewRenderer/bin/Release/net8.0-windows/PreviewRenderer.dll `
            (Join-Path $taskReports 'fixture.png') --smoke-test --independent-operation-checks `
            "--language=$taskLanguage" "--test-profile=$taskProfile"
        if($LASTEXITCODE -ne 0){throw "Independent action fixture failed: $taskLanguage"}
    }
}
finally{Pop-Location}
