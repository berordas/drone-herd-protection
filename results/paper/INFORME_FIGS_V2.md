# INFORME FIGS V2 — figuras corregidas tras la revisión externa (solo lectura + regeneración de PNG; ningún run)

Regeneradas con `figs_paper.py --lang es|en` (mismos nombres, 300 dpi, 8,5 / 17,5 cm; `figs/figs_notas.json` con ambos
idiomas). Cambios: (1a) sin nombres internos de run en ninguna figura ("run principal" / "main run"); (1b) título del panel (a)
del heatmap con el denominador aclarado; (2) rótulos ES de la tira: muestra / suelta / golpe (y "preparado 901 → muestra 1231"
en el supertítulo; anotación "señuelo (muestra)"); (3) leyendas de `fig_tradeoff` (debajo del eje, 2 columnas) y
`fig_tradeoff_ancho` (una sola leyenda bajo los 3 paneles) fuera del área de datos; datos y escalas intactos.

## 1b. Denominadores del panel (a) del heatmap (n = 18…42, suma 200)

**No es un agregado de runs ni un error de conteo**: son los **200 episodios de UNA sola evaluación** — el run principal
(ckpt final) contra Reactive — porque el protocolo evalúa **100 semillas × 2 tipos de episodio {solo-lobos, mixto}**
(los "100 pares" del paper son semillas emparejadas; cada semilla aporta dos episodios). Fuente:
`/data/hrl_m1/eval/manager_M1pppp_final__reactive.json` → `episodes[]`: `Counter(kind) = {lobos: 100, mixto: 100}`, 100
semillas distintas; por (estrato, nº de lobos): S,n=2: 42 · S,n=4: 32 · S,n=3: 28 · G,n=4: 28 · S,n=1: 24 · G,n=3: 18 ·
S,n=5: 16 · G,n=5: 12 (= 200). Los porcentajes del panel salen de `resumen.P_a_first` del mismo JSON. Título nuevo:
"200 episodios = 100 semillas × {lobos, mixto}".

## 5a. Por qué KNC es `None` en la celda "gestor atacante" de la tabla D2

KNC (fracción de muertes cuyo lobo matador **nunca fue confirmado** por la barrera) se calcula en el arnés E0.4
(`/data/hrl_d2/e04.py`) **a partir del registro por muerte `killer_confirmado`** que produce el bucle plano del mundo para
los atacantes scriptados (`run_script`, línea 153: `knc = Σ[not d["killer_confirmado"]]`). Para el atacante "gestor" el
episodio corre dentro de `ManagerEnv` (`run_manager`, líneas 160-185), y ese arnés **no extrae el registro por muerte**, así
que el script fija `"knc": None` (línea 180) y el resumen de la celda deja `knc_frac = None` (líneas 214/225: se agrega solo
sobre episodios con KNC definido). Es decir: **KNC no está definido en esa celda porque no se midió allí, no porque sea 0**.
Nota al pie sugerida: "KNC no se computa para el atacante gestor en la tabla D2: el arnés de esa celda no registra la
confirmación del lobo matador (e04.py); la KNC del gestor lobo sí está medida en su propia evaluación (v3.7, vs Reactive):
**0.363** (`/data/hrl_m1/m1pppp/canal_manager_v37.json` → `auditoria.knc_frac`; oráculo 0.404, `canal_oracle_v37.json`)."

## 5b. Las "dos defensas aprendidas" de la transferencia 1,75 / 1,76

Sí: son los dos **MARL residuales de drones (MAPPO, receta residual sobre la barrera)**, congelados como oponentes en
`hrl/manager_env.py` (líneas 60-61): `RUN02_MODEL = /data/drones/run02_v34/model.zip` (run02, entrenado en el mundo **v3.4**,
20 M pasos-agente, 6 h 03) y `RUN09_MODEL = /data/drones/run09_v35/model.zip` (run09, la misma receta re-entrenada en
**v3.5-sonido**, 20 M pasos, 7 h 57). Evaluaciones: `/data/hrl_m1/eval/manager_M1pppp_final__run02.json` → `resumen.sev =
[1.755, 1.45, 2.07]` y `manager_M1pppp_final__run09.json` → `[1.76, 1.45, 2.08]` (vs Reactive: 1.765). Ambos ckpts van en
`archivo_tfg_modelos.tar.gz` (`drones/run02_v34/model.zip`, `drones/run09_v35/model.zip`). "Nunca vistas" es exacto: el
manager se entrenó solo contra la barrera Reactive (`train_manager.py`, oponente `reactive`).

## Notas
- `results/MANIFEST.md` §3 conserva los sha256 de las figuras **v1** (archivo del 23-08); las v2 sustituyen a las v1 en
  `/data/paper/figs*` y en `results/paper/figs*` — el zip de esta entrega (`figs_v2.zip`) lleva su propio sha256 abajo.
- Los fotogramas re-renderizados de `fig_cebo_frames` (EN) no se tocan; en ES se usa el GIF original.

**Entrega**: `figs_v2.zip` (2.60 MB) — sha256 `436d688d4b72abddefc3e5528f22048f63ced2bd09664445a24f9113256c7327` — contiene `figs/` (ES) y `figs_en/` (EN), `figs_notas.json`, este informe y `figs_paper.py`.
