#!/bin/bash
# Poll rating + episode count for one or more submission ids every 10 min.
# Usage: tools/watch_rating.sh <submission_id> [<submission_id> ...]
cd "$(dirname "$0")/.." && source .venv/bin/activate
[ $# -eq 0 ] && { echo "usage: $0 <submission_id>..."; exit 1; }
for i in $(seq 1 40); do
  TS=$(date +%H:%M)
  SUBS=$(timeout 60 kaggle competitions submissions kaggriculture 2>/dev/null)
  LINE="$TS"
  for S in "$@"; do
    R=$(echo "$SUBS" | awk -v s="$S" '$1==s {print $NF}')
    E=$(timeout 60 kaggle competitions episodes "$S" 2>/dev/null | grep -c COMPLETED)
    LINE="$LINE  [$S rating=${R:-?} eps=$E]"
  done
  echo "$LINE"
  sleep 600
done
