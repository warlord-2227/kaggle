#!/bin/bash
# Every 30 min, save the ListEpisodes JSON of the given submission ids to analysis/data/live/<id>.json (overwrites; full history is in each response).
cd "$(dirname "$0")/.."
while true; do
  for S in "$@"; do
    curl -s -X POST https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes -H 'content-type: application/json' -d "{\"submissionId\": $S}" -o analysis/data/live/$S.json.tmp && [ -s analysis/data/live/$S.json.tmp ] && mv analysis/data/live/$S.json.tmp analysis/data/live/$S.json
    sleep 10
  done
  echo "$(date +%H:%M) saved $*"
  sleep 1800
done
