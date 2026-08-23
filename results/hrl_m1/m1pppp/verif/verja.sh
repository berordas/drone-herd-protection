#!/bin/bash
# Verja de regresion (8 checks) — imprime PASS/FAIL por check y resumen.
cd /workspace
export OMP_NUM_THREADS=1
FAIL=0
for c in face_check.py battery_check.py escort_check.py drone_check.py reactive_check.py \
         wolf_controller_check.py rl_env_check.py hrl/hrl_check.py; do
  if python3 "$c" > "/tmp/verja_$(basename $c .py).log" 2>&1; then
    echo "PASS $c"
  else
    echo "FAIL $c"; tail -15 "/tmp/verja_$(basename $c .py).log"; FAIL=1
  fi
done
[ $FAIL -eq 0 ] && echo "VERJA 8/8 VERDE" || echo "VERJA ROJA"
