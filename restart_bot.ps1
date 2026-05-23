# restart_bot.ps1
# Terminate existing bot processes and launch the bot in the background, redirecting standard output and error.

Write-Host "Invoking kill_bot.ps1..."
. .\kill_bot.ps1

Write-Host "Starting discord_agent_bot.py in the background..."
Start-Process python -ArgumentList "-u", "discord_agent_bot.py" -WorkingDirectory "c:\Users\Suici\Desktop\VagueBotMk3" -RedirectStandardOutput "c:\Users\Suici\Desktop\VagueBotMk3\bot_output.log" -RedirectStandardError "c:\Users\Suici\Desktop\VagueBotMk3\bot_error.log" -WindowStyle Hidden

Write-Host "Bot started successfully. Standard output is redirected to bot_output.log, standard error to bot_error.log."
