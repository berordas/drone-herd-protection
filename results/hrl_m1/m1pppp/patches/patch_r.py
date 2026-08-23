"""Commit R — RELEVO DE CENTINELA (fisica v3.7; decision de diseno del dueno)."""
p = 'world.py'
s = open(p).read()

# 1) precedencia: el anunciado deja de ser comandable
old = """            # PRECEDENCIA: el coordinador NO toca al INVESTIGADOR (reflejo). v3.0 (pieza 5): el dron que
            # ANUNCIA relevo (drone_relief_hold) SÍ sigue comandable — antes se clavaba en su puesto y
            # dejaba un agujero en la barrera; ahora sigue cubriendo/moviéndose hasta el hand-off (el
            # INCOMING lo persigue: su waypoint se actualiza a la posición VIVA del bajo en _step_battery).
            free = ~self.drone_investigating"""
new = """            # PRECEDENCIA: el coordinador NO toca al INVESTIGADOR (reflejo) NI al que ANUNCIÓ relevo.
            # v3.7 (Commit R, RELEVO DE CENTINELA — decisión de diseño del dueño; INVIERTE la pieza 5
            # de v3.0): el que anuncia SE CLAVA en su puesto (waypoint = su posición, fijado al anunciar
            # en _step_battery) y el mundo le RECHAZA comandos hasta el hand-off. Sigue ACTIVE: disuade
            # QUIETO (v3.5: el sonido no exige movimiento). El INCOMING vuela DIRECTO a ese puesto fijo.
            free = ~self.drone_investigating & ~self.drone_relief_hold"""
assert old in s, "R1"; s = s.replace(old, new, 1)

# 2) anuncio: clavar el waypoint en el puesto
old = """        newly = np.where((st == ACTIVE) & (bat <= self.announce_threshold)
                         & ~self.drone_relief_hold & ~self.drone_investigating)[0]
        for i in newly:
            self.drone_relief_hold[i] = True"""
new = """        newly = np.where((st == ACTIVE) & (bat <= self.announce_threshold)
                         & ~self.drone_relief_hold & ~self.drone_investigating)[0]
        for i in newly:
            self.drone_relief_hold[i] = True
            # v3.7: SE CLAVA en su puesto — waypoint = su posición (el vuelo frena y aparca ahí;
            # _apply_drone_actions le rechaza comandos hasta el hand-off).
            self.drone_waypoint[i] = self.drones[i].copy()"""
assert old in s, "R2"; s = s.replace(old, new, 1)

# 3) docstring del relevo en _step_battery
old = """        Relevo (v3.0, pieza 5 — SIN PARÁLISIS): cuando un ACTIVE baja de announce_threshold ANUNCIA
        (drone_relief_hold) y la central DESPACHA al READY más cargado, que VUELA hacia él (INCOMING,
        persiguiendo su posición VIVA — el bajo SIGUE comandable y cubriendo/moviéndose con la barrera;
        antes se clavaba en su puesto = agujero en la defensa). Al estar ENCIMA (<= relay_handoff_tol del
        DRON bajo) -> HAND-OFF: el relevo pasa a ACTIVE y el bajo a RETURNING (vuela a la central; al
        entrar -> CHARGING). Sin reserva lista, el bajo sigue drenando; si llega a ~0 antes del relevo ->
        STRANDED (se congela DONDE ESTÉ, SIN disuadir —ya no es ACTIVE—, hasta el hand-off).
        Cobertura CONTINUA (el bajo no se va hasta que llega el relevo), salvo el hueco del caso STRANDED.\"\"\""""
new = """        RELEVO DE CENTINELA (v3.7, Commit R — decisión de diseño del dueño; INVIERTE la pieza 5 de
        v3.0): cuando un ACTIVE baja de announce_threshold ANUNCIA (drone_relief_hold) y SE QUEDA
        CLAVADO en su puesto (waypoint = su posición; _apply_drone_actions le rechaza comandos) —
        sigue ACTIVE y disuade QUIETO (v3.5: el sonido no exige movimiento). La central DESPACHA al
        READY más cargado, que vuela DIRECTO a las coordenadas de ese puesto (INCOMING; el puesto es
        FIJO — el clavado no se mueve). Al estar ENCIMA (<= relay_handoff_tol) -> HAND-OFF: el relevo
        pasa a ACTIVE EN el puesto y el saliente a RETURNING (vuela a la central; al entrar ->
        CHARGING). PROHIBIDA cualquier recolocación de otros ACTIVE por causa del relevo: cada puesto
        es un sitio fijo, cero intercambios entre activos (el coordinador sigue contando al clavado
        en su formación — su ranura queda ocupada — y en barrera el gobernador del más rezagado
        espera por él). Sin reserva lista, el bajo sigue drenando; si llega a ~0 antes del relevo ->
        STRANDED (se congela, SIN disuadir —ya no es ACTIVE—, hasta el hand-off): STRANDED solo si
        el fresco no llega a tiempo. Cobertura CONTINUA salvo ese caso.\"\"\""""
assert old in s, "R3"; s = s.replace(old, new, 1)

# 4) comentario del hand-off (#4)
old = """        # 4) HAND-OFF: cada relevo INCOMING que ya está ENCIMA de su bajo (<= relay_handoff_tol) toma el puesto
        #    (-> ACTIVE) y libera al bajo (-> RETURNING, a la central). Mientras vuela, el waypoint PERSIGUE al
        #    bajo (v3.0: posición VIVA — el bajo ya no se clava y puede estar moviéndose con la barrera; en la
        #    práctica la línea se recoloca despacio y el INCOMING a 15 m/s lo alcanza). Sin teletransporte."""
new = """        # 4) HAND-OFF: cada relevo INCOMING que ya está ENCIMA del puesto (<= relay_handoff_tol del dron
        #    bajo, CLAVADO en él desde v3.7) toma el puesto (-> ACTIVE) y libera al saliente (-> RETURNING,
        #    a la central). El waypoint apunta al dron bajo = las coordenadas FIJAS del puesto (v3.7: el
        #    clavado no se mueve; para un STRANDED, congelado, es igualmente fijo). Sin teletransporte."""
assert old in s, "R4"; s = s.replace(old, new, 1)

# 5) comentario del anuncio (#6)
old = """        # 6) ACTIVE que baja del umbral -> ANUNCIA relevo (drone_relief_hold) pero SIGUE comandable y
        #    cubriendo/moviéndose con la barrera hasta el hand-off (v3.0, pieza 5: antes se clavaba en su
        #    puesto —waypoint congelado, fuera del free-mask— y dejaba un agujero en la defensa). El flag
        #    solo marca "esperando relevo" (despacho en #7 y exclusión del pool de investigación).
        #    Excluye al investigador: el reflejo tiene precedencia."""
new = """        # 6) ACTIVE que baja del umbral -> ANUNCIA relevo (drone_relief_hold) y SE CLAVA en su puesto
        #    (v3.7, Commit R: waypoint congelado en su posición y fuera del free-mask de comandos; sigue
        #    ACTIVE y disuade quieto). El flag marca "esperando relevo": despacho en #7, exclusión del
        #    pool de investigación y del free-mask. Excluye al investigador: el reflejo tiene precedencia
        #    (anunciará al terminar su investigación)."""
assert old in s, "R5"; s = s.replace(old, new, 1)

# 6) comentario del STRANDED (#8)
old = """). v3.0: como el bajo ya no se clava al anunciar, el
        #    congelado ocurre AQUÍ (antes ya estaba parado en su puesto)."""
new = """). v3.7: el bajo ya estaba CLAVADO en su puesto al
        #    anunciar; aquí solo pierde el estado ACTIVE (deja de disuadir: el hueco honesto del
        #    relevo tardío — STRANDED solo si el fresco no llega a tiempo)."""
assert old in s, "R6"; s = s.replace(old, new, 1)

# 7) comentario del atributo
old = """        self.drone_relief_hold: np.ndarray | None = None # (n_drones,) ACTIVE que ANUNCIÓ relevo y lo espera (v3.0: SIGUE comandable y cubriendo; solo queda fuera del pool de investigación)"""
new = """        self.drone_relief_hold: np.ndarray | None = None # (n_drones,) ACTIVE que ANUNCIÓ relevo y lo espera CLAVADO en su puesto (v3.7 centinela: waypoint congelado, fuera del free-mask de comandos y del pool de investigación; disuade quieto)"""
assert old in s, "R7"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("world.py: R OK")

p = 'coordinators.py'
s = open(p).read()
old = """    Solo comanda a los drones LIBRES (ACTIVE y no-investigando): NO toca el reflejo de investigación (el
    investigador). v3.0 (pieza 5): el dron que ANUNCIÓ relevo sigue siendo comandable (ya no se clava
    esperando; el INCOMING lo persigue). NO toca la física (world.py congelado); construye un array de
    waypoints y deja que la disuasión del mundo haga el trabajo. Parámetros afinables.\"\"\""""
new = """    Solo comanda a los drones LIBRES (ACTIVE y no-investigando): NO toca el reflejo de investigación (el
    investigador). v3.7 (Commit R, RELEVO DE CENTINELA — invierte la pieza 5 de v3.0): el dron que
    ANUNCIÓ relevo queda CLAVADO en su puesto POR EL MUNDO (waypoint congelado; el mundo le rechaza
    comandos hasta el hand-off). El coordinador lo SIGUE contando en su formación (mismo free-mask):
    su ranura queda OCUPADA -> cero recolocaciones de otros ACTIVE por causa del relevo (en patrulla
    nadie se mueve; en barrera el gobernador del más rezagado espera por él de forma natural, y tras
    el hand-off el fresco ocupa la misma ranura). Construye un array de waypoints y deja que la
    disuasión del mundo haga el trabajo. Parámetros afinables.\"\"\""""
assert old in s, "R8"; s = s.replace(old, new, 1)

old = """        w = self.world
        wp = w.drone_waypoint.copy()
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)"""
new = """        w = self.world
        wp = w.drone_waypoint.copy()
        # v3.7: el free-mask INCLUYE al clavado por relevo (drone_relief_hold) A PROPÓSITO — ocupa su
        # ranura en la formación (el mundo ignora el waypoint que se le calcule): así ningún otro
        # ACTIVE cambia de ranura por causa del relevo, y el gobernador de la barrera espera por él.
        free = (w.drone_state == ACTIVE) & (~w.drone_investigating)"""
assert old in s, "R9"; s = s.replace(old, new, 1)
open(p, 'w').write(s)
print("coordinators.py: R OK")
