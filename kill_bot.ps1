# kill_bot.ps1
# Find and terminate any running processes of discord_agent_bot.py

$processes = Get-CimInstance Win32_Process -Filter "CommandLine like '%discord_agent_bot.py%'"
if ($processes) {
    foreach ($proc in $processes) {
        Write-Host "Stopping process ID $($proc.ProcessId)..."
        Stop-Process -Id $proc.ProcessId -Force
    }
    Write-Host "Successfully stopped all running bot instances."
} else {
    Write-Host "No running instances of discord_agent_bot.py found."
}
