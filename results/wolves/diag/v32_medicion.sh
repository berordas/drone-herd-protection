#!/bin/bash
# Medición v3.2 (metro DGX, dentro del contenedor): baseline (Dummy) + reactive_eval, pasada única.
# Uso: docker exec <uid>-wolves bash /data/wolves/diag/v32_medicion.sh <etiqueta>
set -u
cd /workspace
echo "=== PASADA $1: baseline.py (Dummy, 100/tipo) ==="
PYTHONPATH=/workspace python3 baseline.py
echo "===BASELINE_FIN"
echo "=== PASADA $1: reactive_eval.py (Reactive, 100/tipo) ==="
PYTHONPATH=/workspace python3 reactive_eval.py
echo "===REACTIVE_FIN"
