#!/bin/bash
# Evals del STOP-D2: defensa dronemgr (ckpt final) x atacantes {natural, cebo2f, manager}, 100 pares.
cd /workspace
export OMP_NUM_THREADS=1
CK=${1:-/data/hrl_d2/D2/model.zip}
for a in natural cebo2f manager; do
  python3 /data/hrl_d2/e04.py "dronemgr:$CK" $a /data/hrl_d2/e04_dronemgr__${a}.json > /data/hrl_d2/stop_d2_${a}.log 2>&1 &
done
wait
echo "STOP_D2_EVALS_OK"
