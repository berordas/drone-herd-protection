# Imagen del PROYECTO (fase RL de lobos), CALCADA del entorno base del laboratorio
# (~/compose_base_python* en la DGX): misma imagen base, mismos pasos y el MISMO
# requirements.txt (lockfile uv, pins exactos: numpy 2.2.6 / matplotlib 3.10.6 /
# pillow 11.3.0 / torch 2.8.0 / gymnasium 1.2.1 / stable-baselines3 2.7.0 /
# tensorboard 2.20.0). SIN pettingzoo/benchmarl (fase de drones, aún no).
# Instrucciones byte a byte como las del lab -> Docker reutiliza la caché de capas.
FROM quay.io/jupyter/base-notebook

USER root
RUN chown -R 1000:100 /home/jovyan
RUN apt-get update \
    && apt-get install -y sudo \
    && usermod -aG sudo jovyan \
    && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN apt-get install -y build-essential libgmp-dev libcdd-dev git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY requirements.txt /tmp/requirements.txt

RUN uv pip install --system --no-cache-dir setuptools --upgrade 

RUN uv pip install --system --no-cache-dir -r  /tmp/requirements.txt

# libGL/glib para opencv (viene en el lockfile del lab): sin esto, cualquier import de cv2
# (p.ej. el forkserver de SubprocVecEnv re-importando el stack) muere en un servidor sin X.
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# v3.0 (render, pieza 6): fuente de emoji A COLOR — render.py renderiza 🐄🐺🦌🐗🚁 como sprites
# PIL (embedded_color) buscando NotoColorEmoji.ttf en /usr/share/fonts/truetype/noto/; SIN la
# fuente cae al render de marcadores planos (la "regresión" de los GIFs del contenedor). Capa
# separada al final -> la caché de las capas del lab no se invalida. Solo afecta al render.
RUN apt-get update && apt-get install -y fonts-noto-color-emoji && rm -rf /var/lib/apt/lists/*

USER $NB_UID

