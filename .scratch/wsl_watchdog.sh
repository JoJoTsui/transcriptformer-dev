#!/usr/bin/env bash
# WSL flight recorder: snapshot system state every 5s so the next VM stop
# leaves forensic evidence right up to the kill. Appends to the log given as
# $1. Designed to survive the CLI exiting (launch via setsid nohup).
LOG="$1"
while true; do
  {
    echo "=== $(date '+%F %T.%3N')"
    grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|Committed_AS|CommitLimit' /proc/meminfo
    echo "load: $(cat /proc/loadavg)"
    echo "sessions: $(loginctl list-sessions --no-legend 2>/dev/null | wc -l)"
    loginctl list-sessions --no-legend 2>/dev/null
    echo "top-rss:"
    ps -eo pid,rss,comm --sort=-rss | head -4
    echo "dmesg-tail:"
    dmesg -T 2>/dev/null | tail -3 || echo "dmesg unreadable"
  } >> "$LOG" 2>&1
  sleep 5
done
