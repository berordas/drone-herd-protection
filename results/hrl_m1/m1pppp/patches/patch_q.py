"""Commit Q — coste de deliberacion (plan M1'''' del dueno). Ejecutar desde la raiz del repo."""
p = 'hrl/manager_env.py'
s = open(p).read()

old = """OPTION_SPECS = ("""
new = """DELIB_COST = 0.05                  # Commit Q (plan M1'''', dueño): COSTE DE DELIBERACIÓN pre-registrado
                                   # — una decisión tomada tras INTERRUPCIÓN (ABORT) que CAMBIA de opción
                                   # (con acciones discretas, "re-arrancar con parámetros nuevos" = otra
                                   # acción) resta esto a la recompensa del tramo nuevo. Decisiones tras
                                   # terminal NATURAL (MUERTE/HERD_SAFE/techo/FIN) = GRATIS; re-elegir la
                                   # MISMA opción tras ABORT = GRATIS (la capa no re-arranca). Motivo:
                                   # degeneración de opciones (cf. option-critic) — el manager conserva
                                   # TODA la libertad; molinillear se paga, no se prohíbe. FALLBACK ÚNICO
                                   # pre-registrado en PREREGISTRO_v3 (escrito ANTES de entrenar): 0.1 si
                                   # en la ligera de 40k los ABORTs/ep siguen > 10. Los baselines no
                                   # interrumpen => pagan 0 (escalera justa). La SEV de todas las tablas
                                   # es SIEMPRE sin coste (n_depredadas); el coste solo da forma al
                                   # RETORNO de entrenamiento (telemetría: aborts / delib_pagado).
OPTION_SPECS = ("""
assert old in s, "Q1"; s = s.replace(old, new, 1)

old = """                 g_oversample: float | None = None, obs_ablate_progress: bool = False):"""
new = """                 g_oversample: float | None = None, obs_ablate_progress: bool = False,
                 delib_cost: float = DELIB_COST):"""
assert old in s, "Q2"; s = s.replace(old, new, 1)

old = """        self._ablate = bool(obs_ablate_progress)"""
new = """        self._ablate = bool(obs_ablate_progress)
        self._delib_cost = float(delib_cost)             # Commit Q (0.0 = apagado)"""
assert old in s, "Q3"; s = s.replace(old, new, 1)

old = """        self._log: list[dict] = []
        self._penetrado_ticks = 0
        self._info_reset: dict = {}"""
new = """        self._log: list[dict] = []
        self._penetrado_ticks = 0
        self._last_action: int | None = None             # Commit Q: para detectar el CAMBIO tras ABORT
        self._n_aborts = 0
        self._delib_paid = 0.0
        self._info_reset: dict = {}"""
assert old in s, "Q4"; s = s.replace(old, new, 1)

old = """        self._log = []
        self._penetrado_ticks = 0
        self._hunt = {"""
new = """        self._log = []
        self._penetrado_ticks = 0
        self._last_action = None
        self._n_aborts = 0
        self._delib_paid = 0.0
        self._hunt = {"""
assert old in s, "Q5"; s = s.replace(old, new, 1)

old = """        a = int(action)
        assert 0 <= a < N_OPTIONS, a"""
new = """        a = int(action)
        assert 0 <= a < N_OPTIONS, a
        # Commit Q: ¿decisión tras INTERRUPCIÓN (ABORT) que cambia de opción? => coste.
        delib = bool(self._last_event == EV_ABORT and self._last_action is not None
                     and a != self._last_action)"""
assert old in s, "Q6"; s = s.replace(old, new, 1)

old = """        reward = float(w.n_depredadas - deaths0)
        self._decision_idx += 1"""
new = """        reward = float(w.n_depredadas - deaths0) - (self._delib_cost if delib else 0.0)
        if delib:
            self._delib_paid += self._delib_cost
        if event == EV_ABORT:
            self._n_aborts += 1
        self._last_action = a
        self._decision_idx += 1"""
assert old in s, "Q7"; s = s.replace(old, new, 1)

old = """                          "t0": t0, "ticks": ticks, "event": EVENT_NAMES[event], "reward": reward,"""
new = """                          "t0": t0, "ticks": ticks, "event": EVENT_NAMES[event], "reward": reward,
                          "delib": delib,"""
assert old in s, "Q8"; s = s.replace(old, new, 1)

old = """            info["ep_sev"] = int(w.n_depredadas)"""
new = """            info["ep_sev"] = int(w.n_depredadas)     # SIEMPRE sin coste (la sev de las tablas)
            info["aborts"] = int(self._n_aborts)
            info["delib_pagado"] = round(float(self._delib_paid), 4)"""
assert old in s, "Q9"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("manager_env.py: Q OK")

p = 'hrl/train_manager.py'
s = open(p).read()
old = """            "probs": probs, "ents": ents, "hunt": info.get("hunt", {}),
            "jugada": info.get("jugada")}"""
new = """            "probs": probs, "ents": ents, "hunt": info.get("hunt", {}),
            "jugada": info.get("jugada"), "aborts": info.get("aborts", 0),
            "delib": info.get("delib_pagado", 0.0)}"""
assert old in s, "Q10"; s = s.replace(old, new, 1)
old = """            "caza_por_ep": hunt,"""
new = """            "caza_por_ep": hunt,
            "aborts_por_ep": float(np.mean([r["aborts"] for r in res])),
            "delib_por_ep": float(np.mean([r["delib"] for r in res])),"""
assert old in s, "Q11"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("train_manager.py: Q OK")

p = 'hrl/eval_manager.py'
s = open(p).read()
old = """            "hunt": info.get("hunt", {}), "jugada": info.get("jugada")}"""
new = """            "hunt": info.get("hunt", {}), "jugada": info.get("jugada"),
            "aborts": info.get("aborts"), "delib_pagado": info.get("delib_pagado")}"""
assert old in s, "Q12"; s = s.replace(old, new, 1)
old = """            "censura": _censura(recs),"""
new = """            "censura": _censura(recs),
            "aborts_por_ep": float(np.mean([r.get("aborts") or 0 for r in recs])),"""
assert old in s, "Q13"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("eval_manager.py: Q OK")

p = 'hrl/hrl_check.py'
s = open(p).read()
anchor = "class _RotatingManager:"
test = '''def test_QC_coste_deliberacion():
    """Commit Q (plan M1\'\'\'\' del dueño): COSTE DE DELIBERACIÓN — una decisión tomada tras
    INTERRUPCIÓN (ABORT) que CAMBIA de opción paga DELIB_COST; re-elegir la misma opción tras
    ABORT o cambiar tras terminal NATURAL (K_MAX) es gratis. Los baselines re-eligen la misma
    accion => pagan 0 (escalera justa). Dirigido con la condición del ABORT forzada (pre-show).
    La sev (n_depredadas) queda SIEMPRE sin coste."""
    from hrl.manager_env import ManagerEnv, DELIB_COST
    s = _seeds_by_groups("lobos", 1, 1, min_wolves=3)[0]
    env = ManagerEnv(kinds=("lobos",), seed=0, k_max=200)
    env.reset_to(s, "lobos")
    env._bait_failed = lambda: True
    _o, r1, _t, _tr, i1 = env.step(2)                    # 1ª decisión: sin previo => sin coste
    assert i1["event"] == "ABORT_BAIT_FAILED" and abs(r1 - round(r1)) < 1e-9, (r1, i1)
    _o, r2, _t, _tr, i2 = env.step(2)                    # MISMA opción tras ABORT: gratis
    assert i2["event"] == "ABORT_BAIT_FAILED" and abs(r2 - round(r2)) < 1e-9, (r2, i2)
    _o, r3, _t, _tr, i3 = env.step(3)                    # CAMBIO tras ABORT: paga DELIB_COST
    assert abs((r3 - round(r3)) + DELIB_COST) < 1e-9, r3
    env2 = ManagerEnv(kinds=("lobos",), seed=0, fixed_k=60)
    env2.reset_to(s, "lobos")
    _o, q1, _t, _tr, j1 = env2.step(2)
    assert j1["event"] == "K_MAX", j1
    _o, q2, _t, _tr, j2 = env2.step(3)                   # cambio tras terminal NATURAL: gratis
    assert abs(q2 - round(q2)) < 1e-9, q2
    print(f"  [QC] coste de deliberación {DELIB_COST}: cambio tras ABORT paga; misma opción tras "
          f"ABORT y cambio tras K_MAX gratis")


class _RotatingManager:'''
assert anchor in s and "def test_QC_coste_deliberacion" not in s, "Q14"
s = s.replace(anchor, test, 1)
s = s.replace("""    test_S3_censura()
    test_K1_persistencia_sin_proteccion()""",
              """    test_S3_censura()
    test_QC_coste_deliberacion()
    test_K1_persistencia_sin_proteccion()""", 1)
open(p, 'w').write(s)
print("hrl_check.py: Q OK")
