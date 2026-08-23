"""Commit V2 — SENUELO v2 'directo con espera' (Encargo 2, spec congelada; solo capa,
memberships manager/keep — spawn conserva decoy_prowl como espejo bit a bit del script)."""
p = 'hrl/options_wolf.py'
s = open(p).read()

old = """SHOW_STALL_TICKS = 400"""
new = """DECOY_V2_WAIT_BAND = 10.0        # m (SEÑUELO v2, Encargo 2): banda de PARADA sobre decoy_hold_dist —
                                 # dentro de [hold, hold+banda) el señuelo emite desired=0 EXACTO
                                 # (pack_common_tail normaliza a rapidez plena cualquier vector no nulo:
                                 # la espera tiene que ser un CERO duro, no un factor). CALIBRAR.

SHOW_STALL_TICKS = 400"""
assert old in s, "V1"; s = s.replace(old, new, 1)

old = """    def _decide_cebo(self, w) -> tuple[np.ndarray, bool]:"""
new = """    def _decoy_direct(self, w, sel: np.ndarray, desired: np.ndarray) -> None:
        \"\"\"SEÑUELO v2 "directo con espera" (Encargo 2; spec ENCARGO2_SENUELO_V2_SPEC.md; SOLO
        capa, memberships manager/keep — membership=spawn conserva decoy_prowl: es el ESPEJO bit
        a bit del script y B_spawn su listón, documentado). Aproximación en rumbo RECTO al
        centroide del rebaño; se DETIENE en el borde de la zona de merodeo (decoy_hold_dist del
        ACTIVE más cercano — jamás más adentro antes del show: la expulsión a <=20 lo hace
        inviable) y ESPERA QUIETO hasta el STAGED del asalto (latch de siempre); después show +
        ala rota SIN cambios. Se ELIMINA el bordeo perimetral largo (1d de la auditoría: mediana
        10.7 / p90 677 ticks de sobrecoste — bimodal). Anillos: dmin < hold => HUIDA RADIAL pura
        (el blindaje v3.1); [hold, hold+DECOY_V2_WAIT_BAND) => desired = 0 EXACTO (espera; la
        normalización de pack_common_tail exige cero duro); más allá => carga recta al centroide.
        Sin ACTIVE en vuelo: el mismo hold medido al CENTROIDE (conservador, documentado).
        Determinista, SIN RNG.\"\"\"
        hold = float(w.decoy_hold_dist)
        wolves = w.wolves[sel]
        herd_c = self._herd_c(w)
        to_c = herd_c[None, :] - wolves
        dc = np.linalg.norm(to_c, axis=1)
        approach = to_c / np.maximum(dc[:, None], 1e-9)
        act = w.drones[w.drone_state == ACTIVE]
        if act.shape[0] > 0:
            d = np.linalg.norm(wolves[:, None, :] - act[None, :, :], axis=2)
            j = d.argmin(axis=1)
            dmin = d[np.arange(sel.size), j]
            away = wolves - act[j]
            away = away / np.maximum(np.linalg.norm(away, axis=1, keepdims=True), 1e-9)
        else:
            dmin = dc
            away = -approach
        des = np.where((dmin >= hold + DECOY_V2_WAIT_BAND)[:, None], approach, 0.0)
        des = np.where((dmin < hold)[:, None], away, des)    # anillo interior: huida pura v3.1
        desired[sel] = des

    def _decide_cebo(self, w) -> tuple[np.ndarray, bool]:"""
assert old in s, "V2"; s = s.replace(old, new, 1)

old = """        atk1 = atk2 = False
        if decoy_prowling:
            decoy_prowl(w, s1, desired)
        else:"""
new = """        atk1 = atk2 = False
        if decoy_prowling:
            if self._mode == "spawn":
                decoy_prowl(w, s1, desired)              # espejo del script (B_spawn; test [2])
            else:
                self._decoy_direct(w, s1, desired)       # SEÑUELO v2 (Encargo 2, opción A)
        else:"""
assert old in s, "V3"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("options_wolf.py: V2 OK")

p = 'hrl/hrl_check.py'
s = open(p).read()
anchor = "class _RotatingManager:"
test = '''def test_V2_senuelo_directo():
    """SEÑUELO v2 (Encargo 2, opción A del dueño): aproximación RECTA al centroide con ESPERA en
    el borde de merodeo — sin bordeo perimetral. Dirigido (CEBO d180 en S, pre-show): el señuelo
    se ACERCA (>60 m o hasta el borde), NO orbita (barrido angular < 45°; decoy_prowl orbitaba
    por diseño) y jamás baja del anillo de expulsión pre-show. spawn ≡ script queda en [2]."""
    seed = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 180.0, "hold": 50.0}))
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    def herd_c():
        return w.cows[w.cow_alive].mean(axis=0)
    d0 = float(np.linalg.norm(w.wolves[0] - herd_c()))
    angs, dmins, dcs = [], [], []
    for _ in range(4000):
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        if w.wolf_decoy_released or t or tr:
            break
        v = w.wolves[0] - herd_c()
        angs.append(float(np.arctan2(v[1], v[0])))
        dcs.append(float(np.linalg.norm(v)))
        act = w.drones[w.drone_state == ACTIVE]
        if act.shape[0]:
            dmins.append(float(np.linalg.norm(act - w.wolves[0], axis=1).min()))
    assert len(angs) > 50, "ventana pre-show demasiado corta"
    barrido = float(np.rad2deg(np.abs(np.unwrap(np.asarray(angs)) - angs[0]).max()))
    acercamiento = d0 - min(dcs)
    borde = bool(dmins) and min(dmins) <= w.decoy_hold_dist + DECOY_V2_WAIT_BAND + 5.0
    assert acercamiento > 60.0 or borde, (acercamiento, min(dmins) if dmins else None)
    assert barrido < 45.0, f"el señuelo v2 no debe bordear: barrido {barrido:.0f}°"
    assert not dmins or min(dmins) >= w.decoy_hold_dist - 12.0, \\
        f"se metió en la zona de expulsión pre-show: dmin {min(dmins):.1f}"
    print(f"  [V2] señuelo directo: se acercó {acercamiento:.0f} m (d0 {d0:.0f}), barrido "
          f"{barrido:.0f}° (<45), dmin {min(dmins) if dmins else None} — sin bordeo, sin invadir")


class _RotatingManager:'''
assert anchor in s and "def test_V2_senuelo_directo" not in s, "V4"
s = s.replace(anchor, test, 1)
s = s.replace("from hrl.options_wolf import WolfOptionLayer",
              "from hrl.options_wolf import DECOY_V2_WAIT_BAND, WolfOptionLayer", 1)
s = s.replace("""    test_QB_tripwire_show()
    test_K1_persistencia_sin_proteccion()""",
              """    test_QB_tripwire_show()
    test_V2_senuelo_directo()
    test_K1_persistencia_sin_proteccion()""", 1)
open(p, 'w').write(s)
print("hrl_check.py: V2 OK")
