#!/bin/bash
# Hook: Notification
# Executado quando uma operação longa do Claude Code é concluída.
# Emite um sinal visual/sonoro para chamar atenção do usuário.
#
# Como registrar em settings.json:
#   "Notification": [{ "hooks": [{ "type": "command", "command": "bash {VAULT}/_bootstrap/global/hooks/on-notification.sh", "timeout": 5 }] }]
#
# Comportamento por plataforma:
#   Windows (WSL): notificação via PowerShell
#   Linux/Mac: bell no terminal

MSG="${1:-Operação concluída}"

# Tentar Windows toast (WSL)
if command -v powershell.exe &>/dev/null; then
  powershell.exe -Command "
    Add-Type -AssemblyName System.Windows.Forms
    \$notify = New-Object System.Windows.Forms.NotifyIcon
    \$notify.Icon = [System.Drawing.SystemIcons]::Information
    \$notify.BalloonTipTitle = 'Claude Code'
    \$notify.BalloonTipText = '$MSG'
    \$notify.Visible = \$true
    \$notify.ShowBalloonTip(3000)
    Start-Sleep -Milliseconds 3500
    \$notify.Dispose()
  " 2>/dev/null
  exit 0
fi

# Fallback: bell no terminal
printf '\a'
exit 0
