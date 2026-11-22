param([Parameter(Mandatory = $true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$targetRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
foreach ($required in @('backend/app.py', 'esp32_firmware/PlantSense.ino', 'esp32_firmware/config.h')) {
    if (-not (Test-Path -LiteralPath (Join-Path $targetRoot $required))) {
        throw "Not a PlantSense project: missing $required under $targetRoot"
    }
}
$files = @(
    'backend/app.py', 'backend/database.py', 'backend/services.py', 'backend/analysis_worker.py',
    'backend/static/js/dashboard.js',
    'esp32_firmware/PlantSense.ino', 'esp32_firmware/api_client.cpp',
    'esp32_firmware/api_client.h', 'esp32_firmware/camera_handler.cpp',
    'esp32_firmware/wifi_manager.cpp'
)
foreach ($relative in $files) {
    if (-not (Test-Path -LiteralPath (Join-Path $sourceRoot $relative))) { throw "Update package is missing $relative" }
}
$backupRoot = Join-Path $targetRoot ('.update-backups/fast-camera-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
foreach ($relative in ($files + @('esp32_firmware/config.h'))) {
    $existing = Join-Path $targetRoot $relative
    if (Test-Path -LiteralPath $existing) {
        $backup = Join-Path $backupRoot $relative
        New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $existing -Destination $backup
    }
}
foreach ($relative in $files) {
    $target = Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $sourceRoot $relative) -Destination $target -Force
}
$configPath = Join-Path $targetRoot 'esp32_firmware/config.h'
$configText = [IO.File]::ReadAllText($configPath)
$settings = [ordered]@{
    IMAGE_INTERVAL_MS = 5000
    AI_INTERVAL_MS = 300000
    IMAGE_RETRY_INTERVAL_MS = 2000
    HTTP_CONNECT_TIMEOUT_MS = 5000
    TELEMETRY_HTTP_TIMEOUT_MS = 10000
    HTTP_TIMEOUT_MS = 10000
}
foreach ($name in $settings.Keys) {
    $type = if ($name -in @('TELEMETRY_HTTP_TIMEOUT_MS', 'HTTP_TIMEOUT_MS')) { 'uint16_t' } else { 'uint32_t' }
    $replacement = "static constexpr $type $name = $($settings[$name]);"
    $pattern = '(?m)^\s*static\s+constexpr\s+\w+\s+' + [regex]::Escape($name) + '\s*=[^;]*;[^\r\n]*'
    if ([regex]::IsMatch($configText, $pattern)) {
        $configText = [regex]::Replace($configText, $pattern, $replacement)
    } else { $configText += "`r`n$replacement`r`n" }
}
[IO.File]::WriteAllText($configPath, $configText, [Text.UTF8Encoding]::new($false))
$ignorePath = Join-Path $targetRoot '.gitignore'
$ignoreText = if (Test-Path -LiteralPath $ignorePath) { [IO.File]::ReadAllText($ignorePath) } else { '' }
if ($ignoreText -notmatch '(?m)^/\.update-backups/\r?$') {
    [IO.File]::AppendAllText($ignorePath, "`r`n/.update-backups/`r`n", [Text.UTF8Encoding]::new($false))
}
Write-Output "Updated project: $targetRoot"
Write-Output "Previous files backed up at: $backupRoot"
Write-Output 'Your Wi-Fi credentials, API URLs, backend .env, sensor pin settings, database, and uploads were preserved.'
Write-Output 'Restart Flask. Restage esp32_firmware into a folder named PlantSense and upload PlantSense.ino.'
