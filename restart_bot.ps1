# restart_bot.ps1
# Terminate exist
ing bot processes and launch the bot in the background, redirecting standard output and error.

Write-Host "Invoking kill_bot.ps1..."
. .\kill_bot.ps1

Write-Host "Starting discord_agent_bot.py in the background..."
Start-Process "cmd.exe" -ArgumentList "/c python -u discord_agent_bot.py > bot_output.log 2>&1" -WorkingDirectory "c:\Users\Suici\Desktop\VagueBotMk3" -WindowStyle Hidden

Write-Host "Bot started successfully. Standard output is redirected to bot_output.log, standard error to bot_error.log."
