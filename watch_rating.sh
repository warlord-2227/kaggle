#!/bin/bash
cd /home/iwa/working/kaggle && source .venv/bin/activate
for i in $(seq 1 40); do
  TS=$(date +%H:%M)
  SUB=$(timeout 60 kaggle competitions submissions kaggriculture 2>/dev/null | sed -n '3p' | awk '{print $NF}')
  EPS=$(timeout 60 kaggle competitions episodes 56318327 2>/dev/null | grep -c COMPLETED)
  echo "$TS  rating=$SUB  episodes=$EPS"
  sleep 600
done
