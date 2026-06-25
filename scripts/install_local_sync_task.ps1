param(
    [string]$RepositoryPath = "C:\Users\USER\Desktop\AI_project\Googleplaystore_Game_data_collecting"
)

$script = Join-Path $RepositoryPath "scripts\sync_reports.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -RepositoryPath `"$RepositoryPath`""
$morning = New-ScheduledTaskTrigger -Daily -At 6:30AM
$evening = New-ScheduledTaskTrigger -Daily -At 6:30PM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "GooglePlayGameReportsSync" `
    -Action $action `
    -Trigger @($morning, $evening) `
    -Settings $settings `
    -Description "GitHub Actions 수집 결과를 로컬 reports 폴더로 동기화합니다." `
    -Force
