#!/bin/bash
# Verja de regresión (8 checks). Uso: bash tests/run_all.sh   (desde la raíz del repo, dentro del contenedor)
cd "$(dirname "$0")/.." || exit 1
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
FAIL=0
for c in face_check battery_check escort_check drone_check reactive_check wolf_controller_check rl_env_check hrl_check; do
  if python3 "tests/$c.py" > "/tmp/verja_$c.log" 2>&1; then echo "PASS tests/$c.py"; else echo "FAIL tests/$c.py"; tail -15 "/tmp/verja_$c.log"; FAIL=1; fi
done
[ $FAIL -eq 0 ] && echo "VERJA 8/8 VERDE" || { echo "VERJA ROJA"; exit 1; }
