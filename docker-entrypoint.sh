#!/bin/sh
set -eu

mkdir -p output data/raw

if [ "${USE_SYNTHETIC_DATA:-true}" = "true" ]; then
    echo "Iniciando demo con datos sintéticos..."
    python pipeline_incendios_nasa.py --offline
else
    if [ -z "${FIRMS_MAP_KEY:-}" ]; then
        echo "Falta FIRMS_MAP_KEY para iniciar con datos reales." >&2
        exit 1
    fi
    echo "Consultando NASA FIRMS..."
    python pipeline_incendios_nasa.py
fi

echo "Aplicación disponible en http://localhost:8080"
exec python app_server.py
