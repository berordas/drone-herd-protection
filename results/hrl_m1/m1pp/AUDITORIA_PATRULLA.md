# AUDITORÍA DE COBERTURA DE VIGILANCIA EN PATRULLA (Encargo 1, adenda post-visionado seed 84) — 2026-08-20

Ámbito: SOLO patrulla (fase != ESCOLTA); la barrera no se audita (validada por el dueño en
visionado). Métrica por tick: separación euclídea entre vecinos ADYACENTES del anillo (drones
ACTIVE no-investigando; relevos en tránsito fuera). Umbrales: **VIOLACIÓN D > 200 = 2·r_detect**
(pasillo ciego real: el punto medio queda fuera de la vista de ambos) · **AVISO D > 100** (listón
conservador del dueño). Auditor permanente: `PatrolCoverageTracker` (behavior_checks), integrado
en `EpisodeAudit` y en `ManagerEnv` (info["patrulla"]) → **RUN-M1'' y posteriores lo reportan**
(Encargo 1e, commit M). Pasada retroactiva determinista sobre los corpus v3.6 (mismas semillas).

## Tabla (100 semillas/tipo por corpus; sanity = 50 G/n≥3 × 2 brazos)

| corpus | % ticks AVISO | % ticks VIOLACIÓN | D_max | R media / máx | % t en R<71 / 71-142 / >142 | eps con violación | entradas no detectadas (por arco viol / aviso) |
|---|---|---|---|---|---|---|---|
| Reactive-estática (metro v3.6 = A/B estática) | **97.7%** | **0.0%** | 190.9 | 75.4 / 97.0 | 4.4 / 95.6 / 0.0 | 0 | **4** (0 / 4) |
| A/B órbita (contraste, 0.02) | 91.6% | ~0% | 194.6 | 69.3 / 96.6 | 24.4 / 75.6 / 0.0 | 1 | 1 (0 / 1) |
| sanity E0.1 v3.6 (capa K) | 95.8% | 0.0% | 185.4 | 69.0 / 93.0 | 6.7 / 93.3 / 0.0 | 0 | 0 |
| suelo residual δ≡0 (estática) | 97.7% | 0.0% | 190.9 | 75.4 / 97.0 | 4.4 / 95.6 / 0.0 | 0 | 4 (0 / 4) |
| run02 @ estática | 96.7% | 0.0% | 189.8 | 74.0 / 94.8 | 7.1 / 92.9 / 0.0 | 0 | 0 |
| run09 @ estática | 97.0% | 0.0% | 187.2 | 74.3 / 94.9 | 6.1 / 93.9 / 0.0 | 4 | 4 (0 / 4) |

## Lecturas

1. **No hay pasillo ciego real**: 0 ticks de VIOLACIÓN en toda la config estática (D_max 185-191,
   siempre < 200). Geometría: R = spread + r_notice + DETER ⇒ R vive en 69-75 m (máx 97), lejos
   del umbral de violación R≈142. El anillo NUNCA entra en la zona >142.
2. **El listón conservador del dueño (D>100) está superado casi SIEMPRE**: 92-98% del tiempo de
   patrulla (con M=4 y R≈75, D≈1.41·R≈106 — estructural, no episódico). Es decir: la patrulla
   actual vive permanentemente en la zona de AVISO del dueño, y a un paso (R≈71) del OK.
3. **Entradas no detectadas**: 4 en el corpus estático — y las 4 son de UN episodio
   (**seed 77 mixto, sev 8**): 4 lobos llegan a <100 m del rebaño sin haber sido detectados,
   cruzando arcos en AVISO (no ciegos: el hueco está entre el anillo, centrado en el centroide,
   y las reses PERIFÉRICAS — el anillo protege el centroide, no a las rezagadas). GIF:
   `gifs/audit_entradas_s77_mixto_estatica.gif` (+ timeline). En órbita el mismo fenómeno
   aparece 1 vez (seed 84 mixto, sev 0). NO cumple el criterio estricto del GIF ("violaciones"),
   pero es la evidencia pertinente para tu decisión.
4. Contraste órbita vs estática: la órbita pasa más tiempo con R<71 (24% vs 4%) porque el anillo
   gira con radio algo menor de media, pero acumula 1 episodio con ticks de VIOLACIÓN (anillo
   degenerado durante relevos: con la órbita los relevos tardan 3× y dejan M<4 más tiempo).

## DECISIÓN HUMANA PENDIENTE (prohibido arreglar nada)

- ¿Es aceptable vivir en AVISO estructural (D≈106 > 100) sabiendo que el agujero CIEGO (D>200)
  no ocurre nunca? Si quieres D≤100 harían falta más densidad (M>4) o menos radio (R≤71 ⇒
  recortar el término +DETER del radio adaptativo) — **lo decides tú**.
- El caso seed 77 (rezagadas fuera del paraguas del anillo) es un modo de fallo distinto del
  pasillo entre drones: el anillo se ancla al CENTROIDE. Si quieres cobertura de periféricas,
  también es decisión de diseño tuya.

## Encargo 1d — sobrecoste del rodeo del señuelo (evidencia para el Encargo 2)

50 episodios CEBO_keep (sanity v3.6): t(inicio→borde de la zona de merodeo, 150 m del ACTIVE más
cercano) real vs teórico en línea recta a 4 m/s (dist(spawn→posición alcanzada)/0.4):

| | valor |
|---|---|
| alcanzan la zona de merodeo | 50/50 |
| t real medio | 627 ticks |
| t teórico medio | 425 ticks |
| **sobrecoste medio** | **202 ticks** |
| sobrecoste p50 / p90 / máx | **10.7 / 677 / 1078** |

**Bimodal**: la mitad de los señuelos ya van casi rectos (sobrecoste ≈ 0-11 ticks); una cola de
~40% da el bordeo perimetral largo (600-1100 ticks — hasta 2× el tiempo teórico). El señuelo v2
"directo con espera" (Encargo 2, congelado) atacaría exactamente esa cola. Detalle por episodio
en `audit_patrulla_sanity.json` (clave `decoy` de cada episodio CEBO).

*Artefactos*: audit_patrulla_{reactiva,orbita,sanity,floor,run02e,run09e}.json ·
verif/audit_patrulla.py (pasada) · gifs/audit_entradas_s77_mixto_estatica.gif ·
ENCARGO2_SENUELO_V2_SPEC.md (especificación congelada).

---

## FIRMA DEL DUEÑO (2026-08-20) — aceptar y documentar

1. **Regla dura OFICIAL de cobertura: D ≤ 200 entre vecinos del anillo** (= 2·r_detect, el
   pasillo ciego). Cumplida SIEMPRE en el corpus: 0 ticks de violación, D_max 185-191. El listón
   100 queda como **AVISO de monitorización, no objetivo**. Porqué geométrico (anotado): con M
   drones equiespaciados D = 2R·sin(π/M); con M=4, D ≤ 100 exige R ≤ 70.7 m, pero el radio
   adaptativo R = spread + r_notice + DETER ≈ spread + 40 vive en 69-97 m (spread real del
   rebaño) ⇒ D ≈ 98-137: **inalcanzable con M=4 al radio actual**. Para D ≤ 100 con estos R
   haría falta M=6 (D=R ≤ 100) o M=5 con R ≤ 85.
2. **Seed 77 mixto = LIMITACIÓN de la defensa clásica** (para la memoria del TFG): anillo
   anclado al CENTROIDE sin garantía de paraguas sobre reses periféricas — 4 entradas no
   detectadas en 1 episodio de cientos. **Verificación pedida por el dueño (forense_s77.json)**:
   el anillo SÍ estaba a M=3 en las 4 entradas (t=994), pero **NO por investigación de corzo**
   — el corzo se descartó a t=1 (nació junto a un dron). El investigador (dron 2, t=933-1011)
   perseguía al **LOBO SINGLETON** del spawn [1,4]: un **CEBO NATURAL** con lobos scriptados —
   el solitario tira del investigador, el anillo queda a 3, y el paquete de 4 entra por el arco
   debilitado sin ser detectado hasta <100 del rebaño (las 4 entradas caen DENTRO de la ventana
   de investigación). La fase pasó a ESCOLTA a t=1011, 17 ticks después de las entradas.
3. **Sin cambios de código**: el auditor sigue en el arnés tal cual (regla dura D≤200 como
   VIOLACIÓN, 100 como AVISO — exactamente lo ya implementado). **PATRULLA-v2** (anclaje/radio
   adaptativo a la res más lejana) queda como **future work nombrado, no especificado**.
