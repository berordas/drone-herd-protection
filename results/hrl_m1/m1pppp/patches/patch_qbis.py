"""Commit Q-bis — tripwire del show (plan M1'''' + adjudicacion: DEGRADADO a tripwire tras S1)."""
p = 'hrl/options_wolf.py'
s = open(p).read()

old = """ALIGN_T_MAX = 2500               # ticks: techo absoluto de la fase de alineación (causa c)"""
new = """ALIGN_T_MAX = 2500               # ticks: techo absoluto de la fase de alineación (causa c)

SHOW_STALL_TICKS = 400           # Q-bis (plan M1\'\'\'\' del dueño; DEGRADADO a TRIPWIRE tras S1): asalto
                                 # STAGED este nº de ticks ACUMULADOS sin show => show FORZADO + evento
                                 # STALL. Cierre de GUION, no de decisión (la opción ejecuta el cebo
                                 # entero; decidir es del manager, ejecutar es de la opción). Tras S1
                                 # debe disparar ~0: n_stalls es métrica de SALUD y su disparo en eval
                                 # = DECISIÓN HUMANA PENDIENTE (pre-registrado en PREREGISTRO_v3)."""
assert old in s, "B1"; s = s.replace(old, new, 1)

old = """        self.t_staged: int | None = None
        self.t_show: int | None = None
        self.t_suelta: int | None = None
        self.t_strike: int | None = None"""
new = """        self.t_staged: int | None = None
        self.t_show: int | None = None
        self.t_suelta: int | None = None
        self.t_strike: int | None = None
        self._staged_noshow = 0                          # Q-bis: ticks staged acumulados sin show
        self.n_stalls = 0                                # Q-bis: disparos del tripwire (salud)"""
assert old in s, "B2"; s = s.replace(old, new, 1)

old = """            self.t_staged = self.t_show = self.t_suelta = self.t_strike = None   # censura"""
new = """            self.t_staged = self.t_show = self.t_suelta = self.t_strike = None   # censura
            self._staged_noshow = 0
            self.n_stalls = 0"""
assert old in s, "B3"; s = s.replace(old, new, 1)

old = """        self._opt_name, self._opt_params = name, dict(params)
        self._align_done = True                          # (Commit S1) default: sin fase de alineación"""
new = """        self._opt_name, self._opt_params = name, dict(params)
        self._align_done = True                          # (Commit S1) default: sin fase de alineación
        self._staged_noshow = 0                          # (Q-bis) el reloj del tripwire es POR JUGADA"""
assert old in s, "B4"; s = s.replace(old, new, 1)

# El bloque de censura (staged) se muda ANTES del despacho del timing y ahora acumula el
# reloj del tripwire; si llega a SHOW_STALL_TICKS fuerza el show (fluye por el mismo flanco
# SHOW_START de siempre).
old = """        released_before = bool(w.wolf_decoy_released)
        if self._mode == "spawn":"""
new = """        released_before = bool(w.wolf_decoy_released)
        # Censura (hito staged) + TRIPWIRE del show (Q-bis): asalto ESTACIONADO pre-show.
        if not w.wolf_decoy_released and w.pack_prey2 >= 0 and s1.size > 0 and s2.size > 0 \\
                and assault_staged(w, s2, w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind),
                                   stage_hold=self._hold):
            if self.t_staged is None:
                self.t_staged = int(w.step_count)
            self._staged_noshow += 1
            if self._staged_noshow >= SHOW_STALL_TICKS:
                w.wolf_decoy_released = True             # TRIPWIRE: show forzado
                self.n_stalls += 1
                self._staged_noshow = 0
                self.push_event("STALL", tick=int(w.step_count) + 1,
                                ticks_staged=SHOW_STALL_TICKS, mode=self._mode,
                                align_done=self._align_done)
        if self._mode == "spawn":"""
assert old in s, "B5"; s = s.replace(old, new, 1)

old = """        # Hito de censura: primer tick con el asalto ESTACIONADO pre-show (cualquier membership).
        if self.t_staged is None and not w.wolf_decoy_released and w.pack_prey2 >= 0 \\
                and s1.size > 0 and s2.size > 0:
            if assault_staged(w, s2, w._prey_pos_of(w.pack_prey2, w.pack_prey2_kind),
                              stage_hold=self._hold):
                self.t_staged = int(w.step_count)

        atk1 = atk2 = False"""
new = """        atk1 = atk2 = False"""
assert old in s, "B6"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("options_wolf.py: Q-bis OK")

p = 'hrl/manager_env.py'
s = open(p).read()
old = """            info["aborts"] = int(self._n_aborts)"""
new = """            info["aborts"] = int(self._n_aborts)
            info["stalls"] = int(layer.n_stalls)         # Q-bis: tripwire (salud; ~0 esperado)"""
assert old in s, "B7"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("manager_env.py: Q-bis OK")

p = 'hrl/eval_manager.py'
s = open(p).read()
old = """            "aborts": info.get("aborts"), "delib_pagado": info.get("delib_pagado")}"""
new = """            "aborts": info.get("aborts"), "delib_pagado": info.get("delib_pagado"),
            "stalls": info.get("stalls")}"""
assert old in s, "B8"; s = s.replace(old, new, 1)
old = """            "aborts_por_ep": float(np.mean([r.get("aborts") or 0 for r in recs])),"""
new = """            "aborts_por_ep": float(np.mean([r.get("aborts") or 0 for r in recs])),
            "stalls_total": int(sum(r.get("stalls") or 0 for r in recs)),"""
assert old in s, "B9"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("eval_manager.py: Q-bis OK")

p = 'hrl/train_manager.py'
s = open(p).read()
old = """            "jugada": info.get("jugada"), "aborts": info.get("aborts", 0),
            "delib": info.get("delib_pagado", 0.0)}"""
new = """            "jugada": info.get("jugada"), "aborts": info.get("aborts", 0),
            "delib": info.get("delib_pagado", 0.0), "stalls": info.get("stalls", 0)}"""
assert old in s, "B10"; s = s.replace(old, new, 1)
old = """            "aborts_por_ep": float(np.mean([r["aborts"] for r in res])),
            "delib_por_ep": float(np.mean([r["delib"] for r in res])),"""
new = """            "aborts_por_ep": float(np.mean([r["aborts"] for r in res])),
            "delib_por_ep": float(np.mean([r["delib"] for r in res])),
            "stalls_total": int(sum(r["stalls"] for r in res)),"""
assert old in s, "B11"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("train_manager.py: Q-bis OK")

p = 'hrl/hrl_check.py'
s = open(p).read()
anchor = "class _RotatingManager:"
test = '''def test_QB_tripwire_show():
    """Q-bis (plan M1\'\'\'\'; DEGRADADO a TRIPWIRE tras S1): asalto STAGED 400 ticks acumulados sin
    show => show FORZADO + evento STALL (cierre de GUION, no de decisión). Dirigido: la fase de
    alineación se bloquea artificialmente (parche de instancia) para que el gate jamás termine;
    el tripwire debe disparar a los 400 ticks staged y la jugada continuar por el flanco
    SHOW_START de siempre."""
    seed = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    layer = WolfOptionLayer(option=("CEBO", {"delta_deg": 90.0, "hold": 50.0}))
    layer._align_update = lambda w, s2: None             # la alineación JAMÁS termina (dirigido)
    w = build_world(seed, "lobos", wolf_controller=layer)
    coord = SyncedReactiveCoordinator(w)
    w.reset()
    evs = []
    for _ in range(8000):
        _o, _r, t, tr, _i = w.step(coord.act(w.get_observation()))
        evs += layer.pop_events()
        if w.wolf_decoy_released or t or tr:
            break
    stall = [e for e in evs if e["ev"] == "STALL"]
    show = [e for e in evs if e["ev"] == "SHOW_START"]
    assert stall and show, (stall, show, int(w.step_count))
    assert layer.n_stalls == 1 and stall[0]["t"] >= 400, (layer.n_stalls, stall)
    assert not stall[0]["align_done"], stall
    print(f"  [QB] tripwire del show: STALL a t={stall[0]['t']} (400 staged, alineación "
          f"bloqueada) y show forzado a t={show[0]['t']}")


class _RotatingManager:'''
assert anchor in s and "def test_QB_tripwire_show" not in s, "B12"
s = s.replace(anchor, test, 1)
s = s.replace("""    test_QC_coste_deliberacion()
    test_K1_persistencia_sin_proteccion()""",
              """    test_QC_coste_deliberacion()
    test_QB_tripwire_show()
    test_K1_persistencia_sin_proteccion()""", 1)
open(p, 'w').write(s)
print("hrl_check.py: Q-bis OK")
