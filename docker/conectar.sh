#!/bin/bash
# Entra al contenedor del proyecto (levántalo antes: cd docker && docker compose up -d --build).
# Shell como jovyan (uid remapeado al del host) en /workspace (el repo montado).
docker exec -it -u jovyan -w /workspace "${USER}-wolves" bash
