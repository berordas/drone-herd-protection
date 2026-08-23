# PREREGISTRO_v2 — RUN-M1'' (congelado ANTES de lanzar; 2026-08-20)

**Motivo del re-nivelado**: capacidad nueva (regla de caza oportunista) otorgada a TODOS en la
capa + config oficial de patrulla (v3.6 estática) — cambia la interfaz/config, no el criterio.
**Resolución de las compuertas del STOP-NIVELADO**: el dueño visionó la seed 84 (firma 2) y su
adenda post-visionado mantiene RUN-M1'' en curso ("sigue intacto hasta su STOP"), añade el
auditor de patrulla (Encargo 1, ejecutado: commit M + `AUDITORIA_PATRULLA.md`) y congela el
señuelo v2 como decisión del STOP-M1'' (Encargo 2, `ENCARGO2_SENUELO_V2_SPEC.md`). La referencia
de la sanity queda RE-FIJADA a la celda v3.6: Δ(keep−MASA|G, 50 pares) = +1.16 [+0.42, +1.90]
(atribución: patrulla +0.52 · regla K +0.12 · ref v3.5 en las mismas semillas +0.52). Mini-E0.3:
n=2 caza vs Dummy (1.4-2.0) y poco vs la defensa real (0.15-0.18); n=1 ≈ 0 → train n~U{3,4,5}
según el plan, con la evidencia anotada; fallback de quórum CEBO→MASA en la capa (commit N).

## Configuración congelada

- Física **v3.5-sonido** (`8aeaf89`) · config **v3.6-patrol-estatica** (`caeb683`) · capa K con
  regla de caza (`610e6da`) + fallback de quórum (commit N) · auditor de patrulla (commit M) ·
  instrumentación K-bis (`54d2546`).
- Receta EXACTA de M1: PPO SB3 MlpPolicy [64,64], lr 3e-4, γ=1.0, gae_λ=0.95, ent 0.02→0.005,
  clip 0.2, n_steps 256, batch 512, 10 epochs, 24 envs, **120.000 macro-pasos**, terminación por
  evento (K_MAX 4500, ABORT cono ±60°/3-de-4/gracia 50), ckpt 5k, ligera 10k (40 semillas
  fijas, con P(a) estocástica + contadores de caza). Oponente TRAIN: Reactive-estática.
- **TRAIN n ~ U{3,4,5}** (`--wolves-min 3`); EVAL siempre natural U{1..5} con desglose por n.
- Contingencia de currículo: SOLO AVISO en log (jamás auto-activación).

## Listones CONGELADOS (100 semillas emparejadas 0-99 × {lobos, mixto}, capa K, IC bootstrap 10k)

| baseline | vs Reactive-estática | vs run02-eval |
|---|---|---|
| B_masa | 0.57 [0.41, 0.75] | 0.62 [0.46, 0.80] |
| B_spawn | 0.99 [0.72, 1.27] | 0.85 [0.63, 1.09] |
| **B_oracle** | **1.00 [0.74, 1.28]** | **0.91 [0.68, 1.16]** |

Gap de transferencia del oráculo (run02 − Reactive, emparejado): **−0.09** (run02 defiende algo
mejor que la clásica estática contra el cebo). run09 se añade a la tabla en el STOP-M1''
(mismatch de patrulla documentado: dos filas, estática 0.88/0/0.86 y órbita 0.79/0/0.78 en su
metro de drones).

## Compuertas M1''

- **SE RETIRA** "P(MASA|n≤2) alta": sin señal aprendible con retorno 0 (error de diseño previo,
  documentado); además el fallback de quórum hace CEBO ≡ MASA a n≤2 por construcción.
- **Emergencia**: P(cebo|G, n≥3) ≥ 0.8 al final, juzgada NO-vacua JUNTO a Estructura.
- **Estructura**: P(keep|G, n≥3) alta Y P(Δ90|S, n≥3) alta (discrimina estrato); P(Δ180) ≈ 0;
  re-targets con causa "protegida" y cadencia ≥ cooldown (contadores K-bis).
- **Competencia**: ≥ B_spawn con IC emparejado excluyendo 0; no-inferior a B_oracle (δ=0.15);
  superarlo = estrella.
- **Transferencia**: gap Reactive→run02/run09 no peor que el del oráculo.
- **Auditoría**: 0 CRITICAL; churn/re-targets/PENETRADO + **auditor de patrulla** en el informe.

## Predicciones pre-registradas

1. Re-arranques de opción/ep **caen fuerte** vs M1 (la persistencia de presa cierra el
   re-targeting por churn; el ABORT ya no re-apunta nada).
2. Re-targets/ep > 0 con cadencia de caza (≥ cooldown 250) y causa "protegida" — no metrónomo.
3. **Aparece criterio** (Emergencia + Estructura no-vacuas: keep en G, Δ90 en S, sin Δ180).
4. Ventaja vs B_oracle probablemente **MENOR** que el +0.42 de M1 (aquel vivía del exploit).
   **Éxito = estructura + no-inferioridad** (δ=0.15); superar al oráculo = estrella.

## STOP-M1'' — firmas en el orden de siempre

1º aserciones · 2º VISIONADO DEL DUEÑO (log por GIF) · 3º análisis externo. Visionado (INDEX):
gemelo de la seed 21 con la regla nueva (¿giros = "presa protegida"?) · un re-target legítimo en
MASA puro · una re-decisión tras la primera muerte · un relevo completo en patrulla estática ·
primer episodio con cebo aprendido + el peor episodio del manager. El informe presenta además la
decisión del **Encargo 2** (opción A re-medir+PREREGISTRO_v3+relanzar con horas estimadas vs
opción B future work con el GIF de la seed 84), con el sobrecoste 1d como evidencia (mediana
10.7 / p90 677 / máx 1078 ticks — bimodal).

## Cola tras el STOP-M1'' (nada arranca antes de la firma)

RUN-M2 (K=1000 fijo, capa K — ablación de necesidad) → 1 réplica M1'' → (si hay días) M4 (sin
rasgos de progreso). M3 fuera del alcance.

---

## ADENDA DE ADJUDICACIÓN (dueño, escrita 2026-08-20T13:52Z — run a 20k/120k macro-pasos;
## NINGUNA eval final vista; la única lectura hasta ahora es la ligera de monitorización)

**Hecho reconocido**: las cláusulas de Estructura sobre S (P(Δ90|S,n≥3) alta; P(Δ180)≈0) se
calibraron con E0.1 **v3.5**; las celdas S×Δ **NO están medidas en v3.6** (la patrulla estática
movió el paisaje: G/keep +0.85→+1.16). Procedimiento de DESEMPATE, solo para esas cláusulas
(nada más cambia):

1. **Disparo**: en el checkpoint final o mejor, la política ESTOCÁSTICA con entropía condicionada
   **H(a|S, n≥3) < 0.9** prefiere Δ180 sobre Δ90 en S.
2. Entonces, ANTES de adjudicar la cláusula: **medir las celdas S bajo v3.6** — brazos forzados
   MASA / CEBO(Δ90) / CEBO(Δ180), n≥3, **100 pares por brazo**, semillas emparejadas, vs
   Reactive-estática.
3. **Si Δ(Δ180|S) ≥ Δ(Δ90|S)**: la cláusula se evalúa contra el paisaje v3.6 MEDIDO (el manager
   tenía razón). Anotar que **B_oracle juega Δ90 en S** — parte de cualquier ventaja sobre el
   oráculo procede de aquí.
4. **Si no**: la cláusula falla, con evidencia en vez de con creencia.

## Métrica "DESPERTAR TARDÍO" (adenda del dueño; sustituye la lectura canal-B-como-muertes)

Por episodio: en el tick del latch de ESCOLTA, d_min(lobo→rebaño) y nº de lobos ya a <100 NO
detectados previamente (auditor de patrulla). **DESPERTAR TARDÍO := latch con ≥1 entrada no
detectada previa** (mecanismo del seed 77). Tabla por política: episodios afectados, muertes en
ellos, lag (t_latch − t_primera_entrada_no_detectada). La tabla A/B de fases se mantiene tal
cual con la anotación "canal B (muertes) = 0; el fenómeno es LATENCIA, no fase"; KNC por
política y fase como está, con la nota: **"KNC ~×2 al cebar (17.5% MASA → 34% spawn/oracle):
firma del canal trasero"**. INDEX: episodio del manager con entradas no detectadas ↔ GIF del
seed 77, etiquetado "muertes canal B = 0; despertar tardío".
