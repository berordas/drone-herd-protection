#!/bin/bash
# Evals del STOP-M1'''' (tras RUN_DONE): manager final vs 3 defensas + 60k vs reactive +
# B_* vs run09 (columna que faltaba) + canal/despertar del manager y del oráculo.
cd /workspace
export OMP_NUM_THREADS=1
LOG=/data/hrl_m1/m1pppp/renivelado_logs
CK=/data/hrl_m1/M1pppp/model.zip
CK60=/data/hrl_m1/M1pppp/checkpoints/manager_60000.zip
for opp in reactive run02 run09; do
  python3 -m hrl.eval_manager --policy "manager:$CK" --label manager_M1pppp_final --opponent $opp --procs 16 \
      > "$LOG/mgr_final_$opp.log" 2>&1 &
done
python3 -m hrl.eval_manager --policy "manager:$CK60" --label manager_M1pppp_60k --opponent reactive --procs 12 \
    > "$LOG/mgr_60k.log" 2>&1 &
for pol in masa spawn oracle; do
  python3 -m hrl.eval_manager --policy "$pol" --label "${pol}_v37" --opponent run09 --procs 8 \
      > "$LOG/${pol}_run09.log" 2>&1 &
done
wait
echo "EVALS_STOP_OK"
python3 /data/hrl_m1/m1pppp/verif/canal_fases_v37.py "manager:$CK" reactive /data/hrl_m1/m1pppp/canal_manager_v37.json > "$LOG/canal_mgr.log" 2>&1 &
python3 /data/hrl_m1/m1pppp/verif/canal_fases_v37.py oracle reactive /data/hrl_m1/m1pppp/canal_oracle_v37.json > "$LOG/canal_orc.log" 2>&1 &
wait
echo "CANAL_OK"
echo "STOP_EVALS_OK"
