"""hrl/ — Capa de OPCIONES del trabajo jerárquico (HRL) + calibración conductual (Etapa 0).

Un "manager" de alto nivel asignará roles/frentes sobre OPCIONES scripted congeladas:
lobos MASA/CEBO (options_wolf) y reparto de puestos de drones FRENTE/GUARDIA (options_drone).
La Etapa 0 NO entrena ninguna política: construye la capa y CALIBRA el mundo (margen Δ del
cebo como decisión, latencias que fijan K, frontera de quórum, espejo dron, coste de
conmutación). Referencias: docs/INFORME_RECONOCIMIENTO.md y DISEÑO.md.

Reglas de la casa (misión E0): world.py y coordinators.py NO se tocan (se extiende por
subclase aquí, como NonRigidBarrier en rl/); wolf_controllers.py solo recibió el refactor
conducta-preservante del Commit A (fases del cebo como funciones de módulo, bit a bit).
La capa y los eventos NO consumen ningún stream RNG del mundo. Artefactos a /data/hrl_e0/.
"""
