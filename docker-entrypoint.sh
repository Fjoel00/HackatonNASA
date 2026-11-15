#!/bin/sh
set -eu

mkdir -p output data/raw

echo "Procesando cuadrícula de riesgo histórico de NASA FIRMS..."
python procesar_historico_firms.py || true

if [ "${USE_SYNTHETIC_DATA:-true}" = "true" ]; then
    echo "Iniciando pipeline con datos disponibles..."
    python pipeline_incendios_nasa.py --offline || true
else
    if [ -n "${FIRMS_MAP_KEY:-}" ]; then
        echo "Consultando NASA FIRMS en tiempo real..."
        python pipeline_incendios_nasa.py || true
    fi
fi

echo "Compilando interfaz SeMF oficial en output/index.html..."
python generar_app_tactica.py

echo "Aplicación SeMF disponible en http://localhost:8080"
exec python app_server.py
