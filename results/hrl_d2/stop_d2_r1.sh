#!/bin/bash
# Evals del STOP de la RÉPLICA D2 (seed 1): defensa dronemgr (ckpt final de D2_r1) x atacantes {natural, cebo2f, manager},
# 100 pares (mismas semillas que E0.4 y RUN-D2). Salida: e04_dronemgr_r1__<atacante>.json (NO pisa los de RUN-D2).
cd /workspace
export OMP_NUM_THREADS=1
CK=${1:-/data/hrl_d2/D2_r1/model.zip}
for a in natural cebo2f manager; do
  python3 /data/hrl_d2/e04.py "dronemgr:$CK" $a /data/hrl_d2/e04_dronemgr_r1__${a}.json > /data/hrl_d2/stop_d2_r1_${a}.log 2>&1 &
done
wait
echo "STOP_D2_R1_EVALS_OK"
