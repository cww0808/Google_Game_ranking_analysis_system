param(
    [string]$RepositoryPath = "C:\Users\USER\Desktop\AI_project\Googleplaystore_Game_data_collecting"
)

$git = "C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe"
if (-not (Test-Path -LiteralPath $git)) {
    $git = "git"
}

& $git -C $RepositoryPath pull --ff-only
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Output "reports 폴더 동기화 완료: $(Get-Date -Format s)"
