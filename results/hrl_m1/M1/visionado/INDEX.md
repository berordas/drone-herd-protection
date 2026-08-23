# INDEX del visionado — STOP-M1 (manager final vs Reactive v3.5; render: naranja=detectado, rojo=confirmado, anillo=sonido, 🔊)

Timelines en `timelines/`: cada DECISIÓN del manager (tick de inicio, opción, evento terminal, ticks, r) + eventos de la capa (OPTION_START, SHOW_START).
Orden de firmas: 1º aserciones (§6 del informe) · **2º visionado del dueño (esta tabla)** ☐ · 3º `../../STOP_M1_INFORME.md`.

| # | GIF (`gifs/`) | caso | qué mirar | log |
|---|---|---|---|---|
| 1 | `primer_cebo_G_seed2_lobos_sev5` | G, n=3 (oracle sev 5 también) | CEBO_keep t=0 → show t=341 → 1ª muerte t=1331; después re-decisiones Δ90/Δ180/keep cada 50-120 ticks, cada una mata (re-targeting a la más libre) | ☐ |
| 2 | `abort_en_accion_seed88_lobos_sev1` | ABORT_BAIT_FAILED en acción | ver el cono espejo: ≥3 ACTIVE en ±60° del rumbo del asalto con ESCOLTA → aborto a los 50 ticks; qué hace el manager después (no MASA) | ☐ |
| 3 | `S_d90_seed0_lobos_sev0` | S con Δ90 en las 3 primeras decisiones (sev 0) | el re-split en S: ¿se hace ver el tránsito? | ☐ |
| 4 | `peor_manager_seed21_lobos_sev7` | **el caso del mecanismo**: S n=4, manager 7 vs oracle 0 | keep 1.356 ticks → ABORT; luego keep/Δ90 alternos, cada re-arranque re-fija la presa más libre y mata en 80-400 ticks; 7 muertes en ~1.000 ticks con la línea sonando | ☐ |
| 5 | `peor_vs_oracle_seed57_lobos_sev0` | peor Δ vs oracle (manager 0, oracle >0) | dónde pierde el manager: cebo en un spawn donde MASA/Δ90 fijo rendía | ☐ |

(Criterios sin candidato en la eval de 200 episodios: "n=2 con MASA" — el manager nunca elige MASA; "re-decisión tras la 1ª muerte con cambio de opción" queda cubierto por los GIFs 1 y 4.)
Comprobaciones globales: ningún cruce entre drones a 20 m (v3.5); 🔊 en todo dron con lobo a ≤20; naranja/rojo correctos; el asalto entra por espalda/flancos del ancla.
