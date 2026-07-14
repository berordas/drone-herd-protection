"""rl/ — Andamiaje de la fase RL de LOBOS (contra la barrera reactiva congelada, v2.4).

Contiene el controlador aprendible (`rl_wolf_controller`), el envoltorio Gymnasium
(`wolf_env`) y el entrenador (`train_wolves`). NO toca la física del mundo: world.py
sigue congelado (el cap de velocidad prometido para el aprendido vive en la FRONTERA
del controlador — ver rl_wolf_controller.py). Verificado en rl_env_check.py.
"""
