param(
    [string]$BaseUrl = 'http://127.0.0.1:5000',
    [string]$DeviceId = 'plantsense-simulated',
    [string]$DeviceToken = ''
)
$ErrorActionPreference = 'Stop'
$headers = @{}
if ($DeviceToken) { $headers['X-Device-Token'] = $DeviceToken }
$payload = @{
    device_id = $DeviceId
    plant_species = 'Tomato'
    temperature_c = 28
    humidity_pct = 65
    soil_moisture_pct = 42
    light_lux = 4500
    pump_state = 'OFF'
    grow_light_state = 'ON'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/plant/data" -Headers $headers -ContentType 'application/json' -Body $payload
$escapedDevice = [uri]::EscapeDataString($DeviceId)
Invoke-RestMethod -Uri "$BaseUrl/api/plant/latest-data?device_id=$escapedDevice" | ConvertTo-Json -Depth 5
Write-Output "View the dashboard at $BaseUrl/dashboard and select device $DeviceId"
