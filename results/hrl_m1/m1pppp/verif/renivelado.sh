#!/bin/bash
# RE-NIVELADO ÚNICO del paquete M1'''' (tras los commits S1/S2/CENSURA/Q/Q-bis/R/V2).
cd /workspace
export OMP_NUM_THREADS=1
V=/data/hrl_m1/m1pppp/verif
LOG=/data/hrl_m1/m1pppp/renivelado_logs
mkdir -p /data/hrl_m1/m1pppp/metro "$LOG"
set -m

# Lote A: metro (9 piezas) + celdas limpias + sanity, todo en paralelo
for p in dummy reactive floor run02 run02o run09e run09o cebo; do
  python3 "$V/metro_v37.py" "$p" > "$LOG/metro_$p.log" 2>&1 &
done
python3 "$V/celdas_s_v37.py"  > "$LOG/celdas.log" 2>&1 &
python3 "$V/sanity_capa_v37.py" > "$LOG/sanity.log" 2>&1 &
wait
echo "LOTE_A_OK"

# Lote B: listones B_* (eval_manager, 100x2 semillas emparejadas) vs reactive y run02
for pol in masa spawn oracle; do
  python3 -m hrl.eval_manager --policy "$pol" --label "${pol}_v37" --opponent reactive --procs 16 \
      > "$LOG/${pol}_reactive.log" 2>&1 &
done
wait
for pol in masa spawn oracle; do
  python3 -m hrl.eval_manager --policy "$pol" --label "${pol}_v37" --opponent run02 --procs 16 \
      > "$LOG/${pol}_run02.log" 2>&1 &
done
wait
echo "LOTE_B_OK"
echo "RENIVELADO_OK"
