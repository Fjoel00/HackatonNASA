#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SeMF / AURA-FIRE Unified Portal Generator (NASA Space Apps Challenge 2026)
=============================================================================
Arquitectura Final Consolidada en 2 Pestañas de Alto Impacto:
1. 📅 PESTAÑA 1 (INTACTA) — RIESGO HISTÓRICO DE FUEGO (CALENDARIO DE QUEMAS):
   - Layout Split-Screen con Mapa de Selección de Parcela a la derecha.
   - Máscara Geográfica Invertida (oscurece el exterior de Córdoba y San Luis).
   - Herramienta de Selección por Arrastre (Bounding Box) + Selector de Año (2000–2026).
   - Matriz de 52 semanas agrupadas en 12 meses + Curva Estacional SVG (μ ± 1σ).
   - 100% aislada de simulaciones: solo consume datos históricos (historico_riesgo_grid.json).
2. 🛰️🛡️ PESTAÑA 2 — MONITOR NRT & SeMF TÁCTICO (CONSOLA INTEGRADA):
   - Detecciones Satelitales NASA FIRMS (VIIRS 375m + MODIS 1km + Polígonos DBSCAN).
   - Cinemática de Frentes Activos (Superficie ha, Avance km/h, Rumbo Cardinal).
   - Evacuación Vial OSRM (Ruta verde animada, distancia km, ETA minutos, Botón SOS).
   - Inyección Operativa Única: Simula focos satelitales y calcula al instante
     conos de avance Turf.js (1h y 3h) y rutas de escape por carretera sin ruido.
"""

import os
import json

def get_template():
    json_path = os.path.join("output", "dashboard_data.json")
    embedded_data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                embedded_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Aviso leyendo {json_path}: {e}")

    hist_path = os.path.join("output", "historico_riesgo_grid.json")
    embedded_hist = {}
    if os.path.exists(hist_path):
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                embedded_hist = json.load(f)
        except Exception as e:
            print(f"⚠️ Aviso leyendo {hist_path}: {e}")

    json_str = json.dumps(embedded_data, ensure_ascii=False)
    hist_str = json.dumps(embedded_hist, ensure_ascii=False)

    return r'''<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <link rel="icon" href="favicon.ico" type="image/x-icon">
  <title>SeMF / AURA-FIRE | Harmonization of MODIS & VIIRS Hot Spots (NASA Space Apps)</title>

  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            tactical: {
              950: '#060911',
              900: '#0B101D',
              850: '#10172A',
              800: '#162038',
              700: '#233256',
              600: '#334878',
              accent: '#FF4D2D',
              safe: '#10B981',
              warning: '#F59E0B',
              alert: '#EF4444'
            }
          }
        }
      }
    }
  </script>

  <!-- Leaflet 1.9.4 CSS & JS (Sin API Keys) -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <!-- Turf.js 6.5.0 para Geoprocesamiento, Conos Predictivos y Cinemática -->
  <script src="https://unpkg.com/@turf/turf@6.5.0/turf.min.js"></script>

  <style>
    html, body {
      height: 100%;
      width: 100%;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      touch-action: manipulation;
      background-color: #f8fafc;
    }
    #map {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      right: 0;
      width: 100%;
      height: 100%;
      min-height: 100%;
      z-index: 10;
    }
    #cal-map {
      width: 100%;
      height: 100%;
      min-height: 480px;
      background: #f1f5f9;
    }
    .crosshair-cursor {
      cursor: crosshair !important;
    }
    .user-pulse-marker {
      width: 24px;
      height: 24px;
      background: #dc2626;
      border: 3.5px solid #FFFFFF;
      border-radius: 50%;
      box-shadow: 0 0 16px #dc2626;
      animation: pulse-ring 2s infinite;
    }
    @keyframes pulse-ring {
      0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
      70% { box-shadow: 0 0 0 18px rgba(220, 38, 38, 0); }
      100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    .animated-escape-path {
      stroke-dasharray: 8, 8;
      animation: dash-animation 1.2s linear infinite;
    }
    @keyframes dash-animation {
      to { stroke-dashoffset: -16; }
    }
    .tactical-compass-dial {
      position: relative;
      width: 44px;
      height: 44px;
      border-radius: 9999px;
      background: radial-gradient(circle, #1e293b 0%, #0f172a 100%);
      border: 1.5px solid #334155;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.6), 0 2px 6px rgba(0, 0, 0, 0.25);
    }
    .compass-needle {
      transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
      transform-origin: center center;
    }
    .escape-floating-badge {
      background: rgba(15, 23, 42, 0.94);
      color: #34D399;
      border: 1.5px solid #10B981;
      border-radius: 9999px;
      padding: 3px 9px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 10px;
      font-weight: 800;
      white-space: nowrap;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
      transform: translate(-50%, -50%);
      display: inline-block;
      letter-spacing: 0.03em;
    }
    .current-week-pulse {
      animation: border-pulse 1.8s infinite;
    }
    @keyframes border-pulse {
      0% { border-color: rgba(220, 38, 38, 0.4); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
      70% { border-color: rgba(220, 38, 38, 1); box-shadow: 0 0 0 8px rgba(220, 38, 38, 0); }
      100% { border-color: rgba(220, 38, 38, 0.4); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-thumb {
      background: #cbd5e1;
      border-radius: 4px;
    }
    /* Slider de punto único sin barra acumuladora a la izquierda */
    input[type="range"].year-point-slider {
      -webkit-appearance: none;
      appearance: none;
      background: #e2e8f0;
      height: 6px;
      border-radius: 9999px;
      outline: none;
    }
    input[type="range"].year-point-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #dc2626;
      cursor: pointer;
      border: 2px solid #ffffff;
      box-shadow: 0 1px 4px rgba(220, 38, 38, 0.45);
      transition: transform 0.15s ease;
    }
    input[type="range"].year-point-slider::-webkit-slider-thumb:hover {
      transform: scale(1.15);
    }
    input[type="range"].year-point-slider::-moz-range-track {
      background: #e2e8f0;
      height: 6px;
      border-radius: 9999px;
    }
    input[type="range"].year-point-slider::-moz-range-progress {
      background: transparent;
    }
    input[type="range"].year-point-slider::-moz-range-thumb {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #dc2626;
      cursor: pointer;
      border: 2px solid #ffffff;
      box-shadow: 0 1px 4px rgba(220, 38, 38, 0.45);
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 h-full flex flex-col overflow-hidden select-none">

  <!-- ========================================================================= -->
  <!-- NAVBAR PRINCIPAL: BRAND SeMF (ESTILO MOBILE-FIRST / CLEAN FIGMA DESIGN)   -->
  <!-- CERO BOTONES DE DEMO CRÍTICA NI SELECTORES RESIDUALES EN ESTE NIVEL       -->
  <!-- ========================================================================= -->
  <header class="bg-white/95 border-b border-slate-200/80 px-4 py-2.5 z-30 shrink-0 shadow-sm backdrop-blur-md">
    <div class="max-w-[1700px] mx-auto flex flex-wrap items-center justify-between gap-3">

      <!-- Identidad SeMF -->
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center text-xl text-white shadow-md shadow-red-500/25 shrink-0">
          🔥
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-sm font-black tracking-wide text-slate-900">SeMF</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200/80 font-bold">
              NASA Space Apps 2026
            </span>
          </div>
          <div class="text-[11px] text-slate-500 font-medium flex items-center gap-1.5">
            <span>Servicio de Monitoreo de Fuego</span>
            <span class="text-slate-300">•</span>
            <span class="text-slate-700 font-semibold">Córdoba y San Luis</span>
          </div>
        </div>
      </div>

      <!-- 2 Pestañas Unificadas en Píldoras Limpias -->
      <nav class="flex bg-slate-100 p-1 rounded-full border border-slate-200 text-xs font-semibold shadow-inner">
        <button id="tab-btn-calendar" onclick="switchMainTab('calendar')"
                class="view-tab-btn px-4 py-2 rounded-full transition-all duration-200 flex items-center gap-2 bg-red-600 text-white font-bold shadow-md shadow-red-500/30">
          <span>📅</span>
          <span>Calendario de Quemas</span>
        </button>
        <button id="tab-btn-tactical" onclick="switchMainTab('tactical')"
                class="view-tab-btn px-4 py-2 rounded-full transition-all duration-200 flex items-center gap-2 text-slate-600 hover:text-slate-900">
          <span>🛰️🛡️</span>
          <span>SeMF</span>
        </button>
      </nav>

    </div>
  </header>

  <!-- ========================================================================= -->
  <!-- PESTAÑA 1: CALENDARIO DE QUEMAS ("RIESGO HISTÓRICO DE FUEGO")             -->
  <!-- UI Limpia, Mobile-First, Cero Simulaciones, Cero Ruido                    -->
  <!-- ========================================================================= -->
  <section id="view-calendar" class="view-tab flex-1 min-h-0 overflow-y-auto lg:overflow-hidden p-3 sm:p-5 bg-slate-50">
    <div class="max-w-[1700px] mx-auto lg:h-full min-h-0 flex flex-col lg:flex-row gap-5">

      <!-- COLUMNA IZQUIERDA: CONTROLES + KPIS + MATRIZ 52 SEMANAS + CURVA SVG -->
      <div class="w-full lg:w-7/12 lg:h-full min-h-0 lg:overflow-y-auto space-y-4 pr-1 pb-4">

        <!-- Hero Card y Selector de Año -->
        <div class="bg-white border border-slate-200/80 rounded-3xl p-5 shadow-sm space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h1 class="text-xl sm:text-2xl font-black text-slate-900">
                Calendario de focos de incendio - Línea Temporal
              </h1>
              <p class="text-xs text-slate-500 mt-1 max-w-xl">
                Base oficial de 218518 detecciones satelitales
              </p>
            </div>

            <!-- Selector de Control Temporal (Radio Buttons + Controles Dinámicos) -->
            <div class="bg-slate-50 px-4 py-3 rounded-2xl border border-slate-200/80 shrink-0 space-y-2.5 min-w-[270px]">
              <!-- Radio Buttons de Modo -->
              <div class="flex items-center justify-between text-xs font-semibold text-slate-600 border-b border-slate-200/70 pb-2">
                <span>Modo Temporal:</span>
                <div class="flex items-center gap-3 text-[11px]">
                  <label class="flex items-center gap-1.5 cursor-pointer font-bold text-red-600">
                    <input type="radio" name="cal-mode" value="annual" checked onchange="onCalendarModeChange('annual')"
                           class="accent-red-600 cursor-pointer" />
                    <span>Anual (Focos)</span>
                  </label>
                  <label class="flex items-center gap-1.5 cursor-pointer font-medium text-slate-500 hover:text-slate-800">
                    <input type="radio" name="cal-mode" value="interval" onchange="onCalendarModeChange('interval')"
                           class="accent-red-600 cursor-pointer" />
                    <span>Intervalo (Grilla)</span>
                  </label>
                </div>
              </div>

              <!-- Vista Modo Anual (Focos Reales) -->
              <div id="cal-ctrl-annual" class="space-y-2">
                <div class="flex items-center gap-2">
                  <input id="cal-year-slider" type="range" min="2000" max="2026" value="2025" step="1"
                         oninput="onCalendarYearChange(this.value)"
                         class="w-full year-point-slider cursor-pointer" />
                  <select id="cal-year-select" onchange="onCalendarYearChange(this.value)"
                          class="bg-white border border-slate-200 rounded-xl px-2.5 py-1 text-xs font-semibold text-slate-800 outline-none shadow-sm cursor-pointer">
                  </select>
                </div>
                <div class="text-[10px] text-slate-500 flex items-center justify-between">
                  <span class="text-emerald-700 font-semibold flex items-center gap-1">🔥 Focos satelitales reales</span>
                  <span id="cal-annual-pts-count" class="font-bold text-slate-700">6,690 focos</span>
                </div>
              </div>

              <!-- Vista Modo Intervalo (Círculos 15 km) -->
              <div id="cal-ctrl-interval" class="hidden space-y-2">
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="text-[10px] text-slate-400 font-bold block mb-0.5">Desde:</label>
                    <select id="cal-range-from" onchange="onCalendarIntervalChange()"
                            class="w-full bg-white border border-slate-200 rounded-xl px-2 py-1 text-xs font-semibold text-slate-800 outline-none shadow-sm cursor-pointer">
                    </select>
                  </div>
                  <div>
                    <label class="text-[10px] text-slate-400 font-bold block mb-0.5">Hasta:</label>
                    <select id="cal-range-to" onchange="onCalendarIntervalChange()"
                            class="w-full bg-white border border-slate-200 rounded-xl px-2 py-1 text-xs font-semibold text-slate-800 outline-none shadow-sm cursor-pointer">
                    </select>
                  </div>
                </div>
                <div class="text-[10px] text-slate-500 flex items-center justify-between">
                  <span class="text-amber-700 font-semibold flex items-center gap-1">⭕ Grilla ponderada (15 km)</span>
                  <span id="cal-interval-years-count" class="font-bold text-slate-700">23 años</span>
                </div>
              </div>

              <div id="cal-kpi-risk-index" class="text-[11px] text-emerald-700 font-semibold flex items-center gap-1 border-t border-slate-200/50 pt-1.5">
                <span>✓</span> Serie NASA 26 Años (2000–2026)
              </div>
            </div>
          </div>
        </div>

        <!-- 2 Tarjetas KPI Superiores (Focos Armonizados + Energía Térmica) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          <!-- KPI Focos Armonizados -->
          <div class="bg-white border border-slate-200/70 rounded-3xl p-4 shadow-sm hover:shadow-md transition-all">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-500 font-medium">Focos Armonizados</span>
              <div class="w-8 h-8 rounded-2xl bg-orange-50 text-orange-600 flex items-center justify-center text-sm font-bold">
                🛰️
              </div>
            </div>
            <div id="cal-stat-harmonized-hotspots" class="text-2xl font-black text-slate-900 mt-1">
              -- eq
            </div>
            <div id="cal-stat-raw-breakdown" class="text-[11px] text-slate-500 mt-0.5 truncate">
              VIIRS + MODIS eq
            </div>
          </div>

          <!-- KPI Energía Térmica -->
          <div class="bg-white border border-slate-200/70 rounded-3xl p-4 shadow-sm hover:shadow-md transition-all">
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-500 font-medium">Energía Térmica</span>
              <div class="w-8 h-8 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center text-sm font-bold">
                ⚡
              </div>
            </div>
            <div id="cal-stat-fre" class="text-2xl font-black text-red-600 mt-1">
              -- MW
            </div>
            <div class="text-[11px] text-slate-500 mt-0.5">
              FRP Radiativo Total
            </div>
          </div>
        </div>

        <!-- Matriz de 52 Semanas Rotulada "Riesgo histórico de fuego" -->
        <div class="bg-white border border-slate-200/80 rounded-3xl p-5 shadow-sm space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h2 class="text-base font-black text-slate-900 flex items-center gap-2">
                <span>🔥</span> Riesgo histórico de fuego (52 Semanas)
              </h2>
            </div>
            <!-- Glosario de Colores -->
            <div class="flex items-center gap-1.5 flex-wrap text-[10px] font-semibold">
              <span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">Bajo / Óptimo</span>
              <span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">Moderado</span>
              <span class="px-2 py-0.5 rounded-full bg-orange-100 text-orange-800">Alto</span>
              <span class="px-2 py-0.5 rounded-full bg-red-100 text-red-800">Extremo (Veda)</span>
              <span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">⏳ Sin datos</span>
            </div>
          </div>

          <!-- Grilla de 12 Meses -->
          <div id="cal-weeks-grid" class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2"></div>

          <!-- Recuadros "Semana" (con FRP Térmico semanal) y "Anomalía Z-Score" debajo del calendario semanal -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
            <!-- Recuadro 1: Semana + FRP Térmico de la semana elegida -->
            <div class="bg-slate-50 border border-slate-200/70 rounded-3xl p-4 shadow-sm hover:shadow-md transition-all">
              <div class="flex items-center justify-between">
                <span class="text-xs text-slate-500 font-medium">Semana</span>
                <div class="w-8 h-8 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center text-sm font-bold">
                  📅
                </div>
              </div>
              <div id="cal-stat-current-week" class="text-2xl font-black text-slate-900 mt-1">
                Semana 36
              </div>
              <div id="cal-stat-current-month" class="text-[11px] text-slate-500 mt-0.5">
                Ciclo Anual (1–52)
              </div>
              <div class="mt-2 pt-2 border-t border-slate-200/70 flex items-center justify-between text-xs">
                <span class="text-slate-500 font-medium">FRP Térmico Semanal:</span>
                <span id="cal-stat-week-frp" class="font-black text-red-600">-- MW</span>
              </div>
            </div>

            <!-- Recuadro 2: Anomalía Z-Score -->
            <div class="bg-slate-50 border border-slate-200/70 rounded-3xl p-4 shadow-sm hover:shadow-md transition-all">
              <div class="flex items-center justify-between">
                <span class="text-xs text-slate-500 font-medium">Anomalía Z-Score</span>
                <div class="w-8 h-8 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center text-sm font-bold">
                  📊
                </div>
              </div>
              <div id="cal-stat-zscore" class="text-2xl font-black text-emerald-600 mt-1">
                0.00 σ
              </div>
              <div id="cal-stat-zscore-desc" class="text-[11px] text-slate-500 mt-0.5">
                Vs. media histórica
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- COLUMNA DERECHA: Mapa Interactivo con Bounding Box -->
      <div class="w-full lg:w-5/12 min-h-[520px] lg:min-h-0 lg:h-full flex flex-col bg-white border border-slate-200/80 rounded-3xl overflow-hidden shadow-sm">
        <div class="p-4 bg-white border-b border-slate-100 flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div class="text-sm font-black text-slate-900 flex items-center gap-2">
              <span>🗺️</span> Área de interés
            </div>
            <div id="cal-box-coords-label" class="text-xs text-slate-500 mt-0.5"></div>
          </div>
          <div class="flex items-center gap-2">
            <!-- Botón de Acción Principal en Rojo Carmesí Redondeado -->
            <button id="btn-cal-draw-box" onclick="toggleCalendarBoxTool()"
                    class="px-4 py-2 rounded-full text-xs font-bold bg-red-600 hover:bg-red-700 text-white shadow-md shadow-red-500/25 transition-all flex items-center gap-1.5 active:scale-95">
              <span>📐</span>
              <span id="btn-cal-draw-text">Seleccionar área</span>
            </button>
            <button onclick="clearCalendarBox()"
                    class="px-3 py-2 rounded-full text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
              Reiniciar
            </button>
          </div>
        </div>

        <div class="flex-1 relative min-h-[460px]">
          <div id="cal-map" style="position:absolute; inset:0;"></div>
          <div id="cal-drag-hint" class="hidden absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-red-600 text-white px-4 py-2 rounded-full text-xs font-bold shadow-xl pointer-events-none animate-pulse">
            🖱️ Arrastre el cursor sobre el mapa para seleccionar el área
          </div>
        </div>
      </div>

    </div>
  </section>

  <!-- ========================================================================= -->
  <!-- PESTAÑAS 2 Y 3: CONTENEDOR DEL MAPA OPERATIVO (MONITOR NRT + TÁCTICO)     -->
  <!-- ========================================================================= -->
  <div id="view-map-container" class="view-tab flex-1 min-h-0 relative overflow-hidden hidden flex flex-col">

    <!-- BANNER DINÁMICO DE ESTADO (MÁQUINA DE ESTADOS FSM) -->
    <div id="fsm-banner" class="bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white px-4 py-2 border-b border-red-500/50 flex items-center justify-between shrink-0 shadow-md transition-all duration-300">
      <div class="flex items-center gap-3">
        <div id="fsm-icon" class="text-2xl animate-bounce">🚨</div>
        <div>
          <div id="fsm-status-title" class="text-xs font-black uppercase tracking-wider">
            IMPACTO INMINENTE — ZONA ROJA
          </div>
          <div id="fsm-status-desc" class="text-[11px] text-red-100 font-medium">
            Frente de fuego avanzando hacia su ubicación. Evacúe de inmediato por la ruta marcada.
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <!-- Píldora Táctica de Rumbo de Evacuación -->
        <div id="fsm-bearing-pill" class="flex items-center gap-2 bg-black/25 px-3 py-1 rounded-2xl border border-white/25">
          <div id="fsm-bearing-arrow" class="text-emerald-400 font-black text-base transition-transform duration-500 leading-none" style="transform: rotate(0deg);">
            ▲
          </div>
          <div class="text-left">
            <div class="text-[8px] uppercase tracking-wider text-slate-200 font-bold">Rumbo Huida</div>
            <div id="fsm-bearing-text" class="text-xs font-mono font-black tracking-tight text-white leading-tight">
              --
            </div>
          </div>
        </div>

        <div class="text-right bg-black/25 px-3 py-1 rounded-2xl border border-white/25">
          <div class="text-[9px] uppercase tracking-wider text-red-100 font-bold">Tiempo de Impacto (ETA)</div>
          <div id="fsm-eta-display" class="text-lg font-mono font-black tracking-tight text-white">
            -- MIN
          </div>
        </div>
      </div>
    </div>

    <!-- BARRA HUD METEOROLÓGICA (OPEN-METEO + ESTADO SIMULADOR) -->
    <div id="hud-bar" class="bg-white/95 border-b border-slate-200 px-4 py-2 text-xs flex items-center justify-between overflow-x-auto gap-4 shrink-0 shadow-sm">
      <div class="flex items-center gap-3 whitespace-nowrap">
        <div class="flex items-center gap-1.5">
          <span class="text-slate-500 font-medium">💨 Viento:</span>
          <span id="hud-wind-speed" class="text-slate-900 font-black">-- km/h</span>
          <span id="hud-wind-arrow" class="inline-block transition-transform duration-500 text-red-600 font-black">↑</span>
          <span id="hud-wind-dir" class="text-slate-600 font-semibold">--°</span>
        </div>
        <div class="h-3.5 w-px bg-slate-200"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-500 font-medium">🌡️ Temp:</span>
          <span id="hud-temp" class="text-slate-900 font-bold">--°C</span>
        </div>
        <div class="h-3.5 w-px bg-slate-200"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-500 font-medium">💧 HR:</span>
          <span id="hud-humidity" class="text-slate-900 font-bold">--%</span>
        </div>
        <div class="h-3.5 w-px bg-slate-200"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-500 font-medium">🔥 FRP Pico:</span>
          <span id="hud-frp" class="text-red-600 font-black">-- MW</span>
        </div>
        <div class="h-3.5 w-px bg-slate-200"></div>
        <span id="hud-telemetry-mode" class="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold">
          🛰️ Clima Real Open-Meteo
        </span>
        <div class="h-3.5 w-px bg-slate-200"></div>
        <span id="gps-status-badge" class="text-[10px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-bold flex items-center gap-1" title="Estado de geolocalización del usuario">
          📍 GPS: Adquiriendo...
        </span>
      </div>

      <!-- Badge 30-30-30 -->
      <div id="badge-crossover" class="hidden px-2.5 py-0.5 rounded-full bg-red-600 text-white text-[10px] font-black uppercase tracking-wider animate-pulse whitespace-nowrap shadow-sm">
        ⚠️ CONDICIÓN EXTREMA 30-30-30
      </div>
    </div>

    <!-- Contenedor del Mapa Operativo Leaflet -->
    <main class="flex-1 min-h-0 relative overflow-hidden flex flex-col">
      <div id="map"></div>

      <!-- Banner Flotante de Modo Inyección de Foco -->
      <div id="inject-fire-banner" class="hidden absolute top-4 left-1/2 transform -translate-x-1/2 z-30 bg-slate-900/95 text-white px-4 py-2 rounded-full shadow-2xl border border-red-500/50 flex items-center gap-3 text-xs font-bold pointer-events-auto">
        <span class="animate-pulse text-red-400">🎯 Haga clic en cualquier punto del mapa para colocar el foco simulado</span>
        <button onclick="toggleInjectFireMode(false)" class="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full border border-slate-600">Cancelar</button>
      </div>

      <!-- =================================================================== -->
      <!-- OVERLAYS: CONSOLA OPERATIVA (SeMF)                                  -->
      <!-- =================================================================== -->
      <div id="tactical-overlays" class="hidden absolute top-3 left-3 bottom-3 w-[370px] sm:w-[410px] z-20 pointer-events-none flex flex-col">
        <div class="bg-white/95 backdrop-blur-xl rounded-3xl border border-slate-200/80 p-4 shadow-xl pointer-events-auto overflow-y-auto space-y-3.5 max-h-full text-slate-800">

          <!-- SELECTOR COMPACTO DE FRENTES EN ESCENA CON VENTANA 24H -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Frentes en Escena:</span>
              <span id="tactical-window-badge" class="text-[9px] px-2 py-0.5 rounded-full font-bold bg-slate-100 text-slate-600 border border-slate-200" title="Ventana Satelital Táctica">
                ⏱️ Últimas 24h
              </span>
            </div>
            <div id="brigade-cluster-pills" class="flex items-center gap-1.5 overflow-x-auto pb-1"></div>
          </div>

          <!-- BLOQUE 2: CINEMÁTICA Y PROPAGACIÓN DEL FRENTE -->
          <div class="space-y-2 border-t border-slate-100 pt-2.5">
            <div class="flex items-center justify-between">
              <span class="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <span>🔥</span> Cinemática & Avance
              </span>
              <span id="brigade-selected-cluster" class="text-[10px] px-2.5 py-0.5 rounded-full bg-red-50 text-red-700 font-bold border border-red-200">
                FIRE_CLUSTER_001
              </span>
            </div>

            <div id="brigade-location-name" class="text-[11px] text-slate-500 font-semibold truncate">
              Sierras de Córdoba y San Luis
            </div>

            <div class="grid grid-cols-3 gap-2 text-xs">
              <div class="bg-slate-50 p-2.5 rounded-2xl border border-slate-200/70 text-center">
                <span class="text-slate-400 text-[10px] font-medium block">Superficie</span>
                <div id="brigade-area" class="text-slate-900 font-black text-sm">-- ha</div>
              </div>
              <div class="bg-slate-50 p-2.5 rounded-2xl border border-slate-200/70 text-center">
                <span class="text-slate-400 text-[10px] font-medium block">Propagación</span>
                <div id="brigade-sat-speed" class="text-red-600 font-black text-sm">-- km/h</div>
              </div>
              <div class="bg-slate-50 p-2.5 rounded-2xl border border-slate-200/70 text-center">
                <span class="text-slate-400 text-[10px] font-medium block">Avance</span>
                <div id="brigade-spread-dir" class="text-slate-900 font-black text-sm">--</div>
              </div>
            </div>
          </div>

          <!-- BLOQUE 3: RUTA DE ESCAPE VIAL REAL (OSRM) Y SUPERVIVENCIA -->
          <div class="space-y-2.5 border-t border-slate-100 pt-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <span>🧭</span> Brújula & Evacuación Táctica
              </span>
            </div>

            <!-- TARJETA TÁCTICA DE SUPERVIVENCIA: BRÚJULA Y RUMBO -->
            <div id="escape-card-container" class="rounded-2xl p-2.5 border transition-all duration-300 bg-slate-900 text-white border-slate-800 shadow-md">
              <div class="flex items-center gap-3">
                <!-- Mini brújula giroscópica táctica -->
                <div class="tactical-compass-dial flex items-center justify-center shrink-0">
                  <span class="text-[7px] text-slate-400 absolute top-0.5 font-mono font-bold leading-none">N</span>
                  <span class="text-[7px] text-slate-400 absolute bottom-0.5 font-mono font-bold leading-none">S</span>
                  <span class="text-[7px] text-slate-400 absolute left-1 font-mono font-bold leading-none">O</span>
                  <span class="text-[7px] text-slate-400 absolute right-1 font-mono font-bold leading-none">E</span>
                  <div id="escape-compass-needle" class="compass-needle text-emerald-400 text-lg font-black select-none leading-none" style="transform: rotate(0deg);">
                    ▲
                  </div>
                </div>

                <!-- Rumbo y estado de vía -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between gap-1 mb-0.5">
                    <span class="text-[9px] uppercase tracking-wider font-bold text-slate-400">Rumbo de Huida</span>
                    <span id="escape-status-badge" class="text-[9px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      🛡️ Seguro
                    </span>
                  </div>
                  <div id="escape-bearing-label" class="text-sm font-black text-white truncate font-mono">
                    Zona Despejada
                  </div>
                  <div id="escape-subtext" class="text-[10px] text-slate-300 truncate">
                    Sin necesidad de evacuación
                  </div>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <button onclick="openNativeGoogleMaps()"
                      class="bg-slate-900 hover:bg-slate-800 text-white font-bold py-2.5 px-3 rounded-full text-xs flex items-center justify-center gap-1.5 shadow-md transition-all active:scale-95">
                <span>🗺️</span> Abrir en Maps
              </button>
              <button id="btn-pedir-auxilio" onclick="openSosModal()"
                      class="bg-red-600 hover:bg-red-700 text-white font-black py-2.5 px-3 rounded-full text-xs flex items-center justify-center gap-1.5 shadow-md shadow-red-500/30 transition-all active:scale-95">
                <span>🚨</span> PEDIR AUXILIO
              </button>
            </div>
          </div>

          <!-- BLOQUE 4: INYECCIÓN OPERATIVA (DESPLEGABLE CON INTERRUPTOR TIPO ANDROID) -->
          <div class="space-y-2 border-t border-slate-100 pt-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <span>🧪</span> Inyección Operativa
              </span>
              <label class="relative inline-flex items-center cursor-pointer" title="Activar / Desactivar Simulación Operativa">
                <input id="toggle-operational-injection" type="checkbox" class="sr-only peer" onchange="toggleOperationalInjection(this.checked)">
                <div class="w-10 h-5 bg-slate-300 rounded-full peer peer-checked:bg-amber-500 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5 shadow-inner"></div>
              </label>
            </div>

            <div id="injection-panel-body" class="hidden space-y-2.5 pt-1.5">
              <p class="text-[11px] text-slate-500 leading-snug">
                Modo Simulación activo: los focos reales satelitales quedan ocultos para probar escenarios dinámicos controlados.
              </p>

              <!-- Selector de Severidad de Foco -->
              <div class="flex items-center justify-between text-[11px] bg-slate-50 p-2 rounded-xl border border-slate-200/70">
                <span class="font-bold text-slate-700 flex items-center gap-1"><span>🔥</span> Severidad:</span>
                <select id="sim-fire-severity" class="text-[10px] bg-white border border-slate-300 rounded-lg px-2 py-1 font-semibold text-slate-800">
                  <option value="moderate">Moderado (120 MW, ~1.0 km)</option>
                  <option value="critical" selected>Crítico (350 MW, ~2.5 km)</option>
                  <option value="catastrophic">Catastrófico (750 MW, ~4.2 km)</option>
                </select>
              </div>

              <!-- Botones de Acción Táctica -->
              <div class="grid grid-cols-2 gap-2">
                <button id="btn-inject-fire" onclick="toggleInjectFireMode()"
                        class="py-2 px-2.5 rounded-full text-[11px] font-bold bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 transition flex items-center justify-center gap-1 shadow-sm active:scale-95">
                  <span>🎯</span>
                  <span id="btn-inject-fire-text">Plantar en Mapa</span>
                </button>
                <button id="btn-quick-threat-fire" onclick="injectQuickThreatScenario()"
                        class="py-2 px-2.5 rounded-full text-[11px] font-bold bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 transition flex items-center justify-center gap-1 shadow-sm active:scale-95"
                        title="Genera un frente a barlovento amenazando su ubicación">
                  <span>⚡</span>
                  <span>Foco Amenazante</span>
                </button>
              </div>

              <!-- Botón Limpiar Focos Inyectados -->
              <button id="btn-clear-injected-fires" onclick="clearAllInjectedFires()"
                      class="w-full py-1.5 px-3 rounded-full text-[10px] font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition flex items-center justify-center gap-1.5 active:scale-95">
                <span>🗑️</span>
                <span>Limpiar Focos Inyectados (<span id="lbl-injected-count">0</span>)</span>
              </button>

              <!-- Sliders de Inyección Meteorológica -->
            <div class="bg-slate-50 p-3 rounded-2xl border border-slate-200/70 space-y-2.5 text-[11px]">
              <div>
                <div class="flex justify-between text-slate-700 font-medium">
                  <span>💨 Viento:</span>
                  <b id="sim-lbl-wind-speed" class="text-red-600 font-black">32 km/h</b>
                </div>
                <input id="sim-slider-wind-speed" type="range" min="0" max="100" value="32" step="1"
                       oninput="onSimulatorSliderChange()"
                       class="w-full h-1.5 bg-slate-200 rounded-lg accent-red-600 cursor-pointer mt-1" />
              </div>

              <div>
                <div class="flex justify-between text-slate-700 font-medium">
                  <span>🧭 Origen Viento:</span>
                  <b id="sim-lbl-wind-dir" class="text-slate-900 font-black">200° (S→N)</b>
                </div>
                <input id="sim-slider-wind-dir" type="range" min="0" max="359" value="200" step="1"
                       oninput="onSimulatorSliderChange()"
                       class="w-full h-1.5 bg-slate-200 rounded-lg accent-red-600 cursor-pointer mt-1" />
              </div>

              <div class="grid grid-cols-2 gap-2.5">
                <div>
                  <div class="flex justify-between text-slate-700 text-[10px] font-medium">
                    <span>🌡️ Temp:</span>
                    <b id="sim-lbl-temp" class="text-red-600 font-black">33°C</b>
                  </div>
                  <input id="sim-slider-temp" type="range" min="5" max="48" value="33" step="1"
                         oninput="onSimulatorSliderChange()"
                         class="w-full h-1.5 bg-slate-200 rounded-lg accent-red-600 cursor-pointer mt-1" />
                </div>
                <div>
                  <div class="flex justify-between text-slate-700 text-[10px] font-medium">
                    <span>💧 Humedad:</span>
                    <b id="sim-lbl-rh" class="text-emerald-700 font-black">18%</b>
                  </div>
                  <input id="sim-slider-rh" type="range" min="5" max="95" value="18" step="1"
                         oninput="onSimulatorSliderChange()"
                         class="w-full h-1.5 bg-slate-200 rounded-lg accent-emerald-600 cursor-pointer mt-1" />
                </div>
              </div>
            </div>
            </div>
          </div>

        </div>
      </div>

        </div>
      </div>

    </main>
  </div>

  <!-- ========================================================================= -->
  <!-- MODAL DE SOS DE EMERGENCIA                                                -->
  <!-- ========================================================================= -->
  <div id="modal-sos" class="hidden fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-white border border-slate-200 rounded-3xl max-w-sm w-full p-5 space-y-4 shadow-2xl text-slate-800">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <div class="flex items-center gap-2">
          <span class="text-2xl">🚨</span>
          <h3 class="text-sm font-black text-slate-900 uppercase tracking-wider">Despacho de Emergencia SOS</h3>
        </div>
        <button onclick="closeSosModal()" class="text-slate-400 hover:text-slate-700 text-lg font-bold">✕</button>
      </div>

      <div class="text-xs text-slate-700 space-y-2 bg-slate-50 p-3.5 rounded-2xl border border-slate-200/80">
        <div><b>📍 Ubicación GPS:</b> <span id="sos-gps-text" class="font-mono">--</span></div>
        <div><b>⏱️ Tiempo Estimado Impacto:</b> <span id="sos-eta-text" class="text-red-600 font-black">-- min</span></div>
        <div><b>💨 Viento:</b> <span id="sos-wind-text" class="font-semibold">--</span></div>
      </div>

      <div class="space-y-2 text-xs">
        <label class="flex items-center gap-2 text-slate-700 font-medium">
          <input type="checkbox" id="sos-check-people" checked class="rounded accent-red-600">
          <span>Hay personas o familias atrapadas</span>
        </label>
        <label class="flex items-center gap-2 text-slate-700 font-medium">
          <input type="checkbox" id="sos-check-animals" checked class="rounded accent-red-600">
          <span>Hacienda / Animales en riesgo</span>
        </label>
      </div>

      <div class="grid grid-cols-2 gap-2.5 pt-2">
        <button onclick="sendSosWhatsApp()"
                class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 px-3 rounded-full text-xs flex items-center justify-center gap-1.5 shadow-md">
          <span>💬</span> Enviar WhatsApp
        </button>
        <button onclick="sendSosSms()"
                class="bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 px-3 rounded-full text-xs flex items-center justify-center gap-1.5 shadow-md shadow-red-500/30">
          <span>📱</span> SMS Satelital
        </button>
      </div>
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- MOTOR CENTRAL JAVASCRIPT (3 PESTAÑAS + CALENDARIO AISLADO + SIMULADOR)    -->
  <!-- ========================================================================= -->
  <script>
    window.PRELOADED_DASHBOARD_DATA = ''' + json_str + r''';
    window.PRELOADED_HISTORICAL_GRID = ''' + hist_str + r''';

    // Siluetas geográficas reales simplificadas de las Provincias de Córdoba y San Luis (IGN)
    const PROVINCIAS_CBA_SL_POLYS = {
      cordoba: [
        [-29.50, -65.75], [-29.50, -63.80], [-29.85, -62.10], [-30.65, -61.80],
        [-31.80, -61.75], [-33.30, -61.75], [-34.98, -63.38], [-35.00, -65.10],
        [-32.95, -65.12], [-31.90, -65.18], [-30.60, -65.65], [-29.50, -65.75]
      ],
      sanLuis: [
        [-31.88, -67.35], [-31.90, -65.18], [-32.95, -65.12], [-35.00, -65.10],
        [-36.00, -65.10], [-36.00, -66.85], [-34.60, -67.30], [-33.10, -67.35],
        [-31.88, -67.35]
      ]
    };

    const AppState = {
      currentTab: 'calendar',
      dashboardData: window.PRELOADED_DASHBOARD_DATA || {},
      historicalGrid: window.PRELOADED_HISTORICAL_GRID || {},
      // Estado exclusivo de la Pestaña 1 (Calendario Histórico)
      calendar: {
        mode: 'annual', // 'annual' | 'interval'
        selectedYear: '2025',
        rangeFrom: 2018,
        rangeTo: 2025,
        selectedBounds: null,
        selectedWeek: 36,
        isDrawingBox: false,
        dragStart: null,
        rectLayer: null,
        cellsLayer: null
      },
      // Estado de la Pestaña SeMF (Monitor + Táctico + Simulador)
      selectedCluster: null,
      injectedClusters: [],
      injectedPoints: [],
      isOperationalInjectionActive: false,
      isInjectingFire: false,
      isUsingInjectedWeather: false,
      isRealGpsActive: false,
      userGpsAccuracy: null,
      gpsAccuracyCircle: null,
      _hasInitiallyCentered: false,
      userLocation: { lat: -33.2380, lon: -65.9510 },
      userMarker: null,
      weather: {
        windSpeedKmh: 32.0,
        windDirectionDeg: 200.0,
        temperatureC: 33.5,
        relativeHumidity: 18.0
      },
      layers: {
        viirsPoints: null,
        modisPoints: null,
        firePolygons: null,
        projectionCones: null,
        safeZones: null,
        escapeRoute: null
      },
      currentSafeZoneTarget: null,
      routeRequestSeq: 0,
      CORDOBA_SANLUIS_BOUNDS: L.latLngBounds(
        L.latLng(-36.05, -67.55),
        L.latLng(-29.40, -61.65)
      )
    };

    let map = null;
    let calMap = null;

    function safeRun(label, fn) {
      try { return fn(); } catch (err) { console.error(`[SeMF] Falló ${label}:`, err); }
    }

    window.addEventListener('DOMContentLoaded', async () => {
      // 1) Calendario primero: nunca depende de red externa
      safeRun('initCalendarYearControls', initCalendarYearControls);
      safeRun('initCalendarMap', initCalendarMap);
      try { await ensureHistoricalGridLoaded(); } catch (e) { console.warn('[SeMF] Grilla histórica:', e); }
      safeRun('renderCalendar', renderCalendar);
      safeRun('switchMainTab', () => switchMainTab('calendar'));

      // 2) Mapa operativo (Pestañas 2 y 3): aislado para no bloquear el Calendario
      safeRun('initMap', initMap);
      safeRun('loadActiveFireData', loadActiveFireData);
      refreshDataSourceStatus().catch(e => console.warn('[SeMF] Estado backend:', e));
      try { await fetchRealWeather(); } catch (e) { console.warn('[SeMF] Open-Meteo:', e); }
      safeRun('recalculatePredictiveEngine', recalculatePredictiveEngine);
      safeRun('requestUserRealLocation', () => requestUserRealLocation(false));
    });

    window.addEventListener('resize', () => {
      if (calMap) calMap.invalidateSize(true);
      if (map) map.invalidateSize(true);
    });

    // =========================================================================
    // SECCIÓN 1: GESTIÓN DE FUENTE DE DATOS NRT (API BACKEND)
    // =========================================================================
    async function refreshDataSourceStatus() {
      const label = document.getElementById('data-source-status');
      try {
        const response = await fetch('/api/status');
        if (!response.ok) return;
        const status = await response.json();
        document.getElementById('data-source-select').value = status.mode || 'synthetic';
        if (status.running) {
          label.innerText = 'Procesando…';
          label.className = 'text-[10px] font-mono text-amber-300';
          setTimeout(refreshDataSourceStatus, 2000);
        } else {
          label.innerText = status.error ? `Error: ${status.error}` : (status.mode === 'firms' ? 'FIRMS Real' : 'Demo NRT');
          label.className = `text-[10px] font-mono ${status.error ? 'text-red-400' : 'text-emerald-400'}`;
        }
      } catch (error) {
        label.innerText = 'Modo Local';
        label.className = 'text-[10px] font-mono text-emerald-400';
      }
    }

    async function runDataSource() {
      const button = document.getElementById('data-source-run');
      const label = document.getElementById('data-source-status');
      const mode = document.getElementById('data-source-select').value;
      button.disabled = true;
      button.innerText = 'Procesando…';
      label.innerText = 'Ejecutando pipeline…';
      label.className = 'text-[10px] font-mono text-amber-300';
      try {
        const response = await fetch('/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'No se pudo iniciar el análisis');
        const poll = async () => {
          const statusResponse = await fetch('/api/status');
          const status = await statusResponse.json();
          if (status.running) {
            await new Promise(resolve => setTimeout(resolve, 1500));
            return poll();
          }
          if (status.error) throw new Error(status.error);
          window.location.reload();
        };
        await poll();
      } catch (error) {
        label.innerText = error.message;
        label.className = 'text-[10px] font-mono text-red-400';
        button.disabled = false;
        button.innerText = 'Aplicar';
      }
    }

    // =========================================================================
    // SECCIÓN 2: CONMUTADOR DE LAS 3 PESTAÑAS SEPARADAS
    // =========================================================================
    function switchMainTab(tabName) {
      AppState.currentTab = tabName;
      document.querySelectorAll('.view-tab-btn').forEach(btn => {
        btn.classList.remove('bg-red-600', 'text-white', 'shadow-md', 'shadow-red-500/30');
        btn.classList.add('text-slate-600', 'hover:text-slate-900');
      });
      const activeBtn = document.getElementById(`tab-btn-${tabName}`);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-600', 'hover:text-slate-900');
        activeBtn.classList.add('bg-red-600', 'text-white', 'shadow-md', 'shadow-red-500/30');
      }

      const calView = document.getElementById('view-calendar');
      const mapView = document.getElementById('view-map-container');
      const tacOverlays = document.getElementById('tactical-overlays');
      const fsmBanner = document.getElementById('fsm-banner');

      if (tabName === 'calendar') {
        calView.classList.remove('hidden');
        mapView.classList.add('hidden');
        [80, 250].forEach(ms => setTimeout(() => { if (calMap) calMap.invalidateSize(true); }, ms));
      } else if (tabName === 'tactical' || tabName === 'monitor') {
        calView.classList.add('hidden');
        mapView.classList.remove('hidden');
        if (tacOverlays) tacOverlays.classList.remove('hidden');
        if (fsmBanner) fsmBanner.classList.remove('hidden');
        if (!AppState.isRealGpsActive && !AppState.isOperationalInjectionActive) {
          requestUserRealLocation(false);
        }
        setTimeout(() => { if (map) map.invalidateSize(true); }, 80);
        setTimeout(() => {
          if (map) map.invalidateSize(true);
          safeRun('recalculatePredictiveEngine', recalculatePredictiveEngine);
        }, 250);
      }
    }

    function changeRegion(regionKey) {
      const label = document.getElementById('label-region-info');
      const regions = {
        'Sierras_Cordoba_SanLuis': { name: 'Sierras de Córdoba y San Luis', lat: -32.25, lon: -65.05, zoom: 8 },
        'Trapiche_SanLuis': { name: 'El Trapiche / Potrero (San Luis)', lat: -33.20, lon: -66.15, zoom: 12 },
        'Traslasierra_Cordoba': { name: 'Traslasierra / Mina Clavero (Córdoba)', lat: -31.72, lon: -65.00, zoom: 12 },
        'Cordoba_SierrasChicas': { name: 'Sierras Chicas / Punilla (Córdoba)', lat: -31.22, lon: -64.42, zoom: 12 }
      };
      const cfg = regions[regionKey] || regions['Sierras_Cordoba_SanLuis'];
      if (label) label.innerText = cfg.name;
      if (map) map.setView([cfg.lat, cfg.lon], cfg.zoom);
      if (calMap) calMap.setView([cfg.lat, cfg.lon], Math.max(7, cfg.zoom - 1));
    }

    // =========================================================================
    // SECCIÓN 3: PESTAÑA 1 (APARTADA) — CALENDARIO HISTÓRICO + MÁSCARA + BBOX
    // =========================================================================
    function initCalendarYearControls() {
      // 1) Selector de Año Individual (2000–2026)
      const sel = document.getElementById('cal-year-select');
      if (sel) {
        sel.innerHTML = '';
        for (let yr = 2026; yr >= 2000; yr--) {
          const opt = document.createElement('option');
          opt.value = String(yr);
          opt.innerText = String(yr);
          if (yr === 2025) opt.selected = true;
          sel.appendChild(opt);
        }
      }

      // 2) Selectores de Intervalo de Años (Desde / Hasta)
      const selFrom = document.getElementById('cal-range-from');
      const selTo = document.getElementById('cal-range-to');
      if (selFrom && selTo) {
        selFrom.innerHTML = '';
        selTo.innerHTML = '';
        for (let yr = 2000; yr <= 2026; yr++) {
          const optF = document.createElement('option');
          optF.value = String(yr);
          optF.innerText = String(yr);
          if (yr === 2003) optF.selected = true;
          selFrom.appendChild(optF);

          const optT = document.createElement('option');
          optT.value = String(yr);
          optT.innerText = String(yr);
          if (yr === 2025) optT.selected = true;
          selTo.appendChild(optT);
        }
      }
    }

    function onCalendarModeChange(mode) {
      AppState.calendar.mode = mode;
      const ctrlAnnual = document.getElementById('cal-ctrl-annual');
      const ctrlInterval = document.getElementById('cal-ctrl-interval');

      if (mode === 'annual') {
        if (ctrlAnnual) ctrlAnnual.classList.remove('hidden');
        if (ctrlInterval) ctrlInterval.classList.add('hidden');
      } else {
        if (ctrlAnnual) ctrlAnnual.classList.add('hidden');
        if (ctrlInterval) ctrlInterval.classList.remove('hidden');
      }
      renderCalendar();
    }

    function onCalendarIntervalChange() {
      const selFrom = document.getElementById('cal-range-from');
      const selTo = document.getElementById('cal-range-to');
      let fromY = parseInt(selFrom.value);
      let toY = parseInt(selTo.value);

      if (fromY > toY) {
        toY = fromY;
        selTo.value = String(toY);
      }

      AppState.calendar.rangeFrom = fromY;
      AppState.calendar.rangeTo = toY;

      const badge = document.getElementById('cal-interval-badge');
      if (badge) badge.innerText = `${fromY}–${toY}`;

      const countBadge = document.getElementById('cal-interval-years-count');
      if (countBadge) countBadge.innerText = `${toY - fromY + 1} años`;

      renderCalendar();
    }

    function onCalendarYearChange(val) {
      AppState.calendar.selectedYear = String(val);
      const badge = document.getElementById('cal-year-badge');
      const slider = document.getElementById('cal-year-slider');
      const select = document.getElementById('cal-year-select');

      if (val === 'ALL') {
        if (badge) badge.innerText = 'Promedio 2012–2026';
        if (select) select.value = 'ALL';
      } else {
        if (badge) badge.innerText = String(val);
        if (slider) slider.value = String(val);
        if (select) select.value = String(val);
      }
      renderCalendar();
    }

    async function ensureHistoricalGridLoaded() {
      if (AppState.historicalGrid && Array.isArray(AppState.historicalGrid.cells) && AppState.historicalGrid.cells.length > 0) {
        renderCalendarCellsOnMap();
        return;
      }
      try {
        const res = await fetch('./historico_riesgo_grid.json');
        if (res.ok) {
          AppState.historicalGrid = await res.json();
          renderCalendarCellsOnMap();
        }
      } catch (e) {
        console.warn("Usando baseline embebida para el calendario:", e);
      }
    }

    function addProvinceMaskToMap(targetMap) {
      const worldRing = [[-90, -180], [-90, 180], [90, 180], [90, -180]];
      // Unión de Córdoba y San Luis como ventana iluminada
      const cbaSlWindow = [
        [-29.45, -65.80], [-29.45, -63.75], [-29.85, -62.05], [-30.65, -61.75],
        [-33.30, -61.75], [-35.00, -63.35], [-36.02, -65.08], [-36.02, -66.90],
        [-34.60, -67.35], [-31.85, -67.40], [-31.85, -65.20], [-30.60, -65.70],
        [-29.45, -65.80]
      ];
      L.polygon([worldRing, cbaSlWindow], {
        stroke: false,
        fillColor: '#334155',
        fillOpacity: 0.38,
        interactive: false
      }).addTo(targetMap);

      // Contorno de Córdoba y San Luis + límite interprovincial
      L.polygon(PROVINCIAS_CBA_SL_POLYS.cordoba, {
        color: '#dc2626', weight: 2.0, fill: false, dashArray: '4,4', interactive: false
      }).addTo(targetMap);
      L.polygon(PROVINCIAS_CBA_SL_POLYS.sanLuis, {
        color: '#2563eb', weight: 2.0, fill: false, dashArray: '4,4', interactive: false
      }).addTo(targetMap);
    }

    function initCalendarMap() {
      calMap = L.map('cal-map', {
        preferCanvas: true,
        center: [-32.35, -64.95],
        zoom: 7,
        minZoom: 6,
        maxZoom: 15,
        maxBounds: AppState.CORDOBA_SANLUIS_BOUNDS.pad(0.08),
        maxBoundsViscosity: 1.0
      });

      const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri World Imagery',
        maxZoom: 19
      });

      const osmTiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19
      }).addTo(calMap);

      L.control.layers({
        "🛰️ Satélite Esri": esriSat,
        "🗺️ Calles OSM": osmTiles
      }, null, { position: 'bottomright' }).addTo(calMap);

      addProvinceMaskToMap(calMap);
      AppState.calendar.cellsLayer = L.layerGroup().addTo(calMap);

      // Eventos de Selección por Arrastre (Bounding Box)
      calMap.on('mousedown', (e) => {
        if (!AppState.calendar.isDrawingBox && !e.originalEvent.shiftKey) return;
        AppState.calendar.dragStart = e.latlng;
        if (AppState.calendar.rectLayer) {
          calMap.removeLayer(AppState.calendar.rectLayer);
        }
        AppState.calendar.rectLayer = L.rectangle([e.latlng, e.latlng], {
          color: '#dc2626',
          weight: 2.5,
          fillColor: '#dc2626',
          fillOpacity: 0.18
        }).addTo(calMap);
        calMap.dragging.disable();
      });

      calMap.on('mousemove', (e) => {
        if (!AppState.calendar.dragStart || !AppState.calendar.rectLayer) return;
        AppState.calendar.rectLayer.setBounds(L.latLngBounds(AppState.calendar.dragStart, e.latlng));
      });

      calMap.on('mouseup', (e) => {
        if (!AppState.calendar.dragStart) return;
        const bounds = L.latLngBounds(AppState.calendar.dragStart, e.latlng);
        AppState.calendar.dragStart = null;
        AppState.calendar.selectedBounds = bounds;
        calMap.dragging.enable();
        toggleCalendarBoxTool(false);

        const sw = bounds.getSouthWest();
        const ne = bounds.getNorthEast();
        const kmLat = Math.abs(ne.lat - sw.lat) * 111.0;
        const kmLon = Math.abs(ne.lng - sw.lng) * 111.0 * Math.cos(((sw.lat + ne.lat) / 2) * Math.PI / 180);
        const areaKm2 = Math.max(1, Math.round(kmLat * kmLon));
        const coordText = `Coordenadas [${sw.lat.toFixed(2)}, ${sw.lng.toFixed(2)}] a [${ne.lat.toFixed(2)}, ${ne.lng.toFixed(2)}] (~${areaKm2.toLocaleString()} km²)`;
        const coordsLabel = document.getElementById('cal-box-coords-label');
        if (coordsLabel) coordsLabel.innerText = coordText;
        const parcelAreaEl = document.getElementById('cal-stat-parcel-area');
        if (parcelAreaEl) parcelAreaEl.innerText = coordText;
        renderCalendar();
      });
    }

    function toggleCalendarBoxTool(force) {
      AppState.calendar.isDrawingBox = typeof force === 'boolean' ? force : !AppState.calendar.isDrawingBox;
      const hint = document.getElementById('cal-drag-hint');
      const txt = document.getElementById('btn-cal-draw-text');
      const btn = document.getElementById('btn-cal-draw-box');
      const container = calMap ? calMap.getContainer() : null;

      if (AppState.calendar.isDrawingBox) {
        hint.classList.remove('hidden');
        txt.innerText = 'Cancelar Selección';
        btn.classList.remove('bg-red-600', 'hover:bg-red-700');
        btn.classList.add('bg-slate-800', 'hover:bg-slate-900');
        if (container) container.classList.add('crosshair-cursor');
      } else {
        hint.classList.add('hidden');
        txt.innerText = 'Seleccionar área';
        btn.classList.remove('bg-slate-800', 'hover:bg-slate-900');
        btn.classList.add('bg-red-600', 'hover:bg-red-700');
        if (container) container.classList.remove('crosshair-cursor');
      }
    }

    function clearCalendarBox() {
      if (AppState.calendar.rectLayer && calMap) {
        calMap.removeLayer(AppState.calendar.rectLayer);
        AppState.calendar.rectLayer = null;
      }
      AppState.calendar.selectedBounds = null;
      const coordsLabel = document.getElementById('cal-box-coords-label');
      if (coordsLabel) coordsLabel.innerText = '';
      const parcelAreaEl = document.getElementById('cal-stat-parcel-area');
      if (parcelAreaEl) parcelAreaEl.innerText = 'Región: Provincias de Córdoba y San Luis';
      renderCalendar();
    }

    function renderCalendarCellsOnMap() {
      if (!calMap || !AppState.calendar.cellsLayer) return;
      AppState.calendar.cellsLayer.clearLayers();
      const cells = (AppState.historicalGrid && AppState.historicalGrid.cells) || [];
      const pointsByYear = (AppState.historicalGrid && AppState.historicalGrid.points_by_year) || {};
      const bounds = AppState.calendar.selectedBounds;
      const isAnnual = (AppState.calendar.mode === 'annual');
      const selYear = AppState.calendar.selectedYear;

      if (isAnnual && selYear !== 'ALL') {
        // MODO 1: DIBUJAR TODOS LOS FOCOS PUNTUALES REALES DE ESE AÑO
        const points = pointsByYear[selYear] || [];
        let renderedPoints = 0;

        points.forEach(pt => {
          const [lat, lon, frp, wk, iso_date] = pt;
          if (bounds && !bounds.contains([lat, lon])) return;
          renderedPoints++;

          let fillColor = '#eab308';
          let strokeColor = '#ca8a04';
          let radius = 2.8;

          if (frp >= 50) {
            fillColor = '#dc2626';
            strokeColor = '#991b1b';
            radius = 4.6;
          } else if (frp >= 15) {
            fillColor = '#f97316';
            strokeColor = '#c2410c';
            radius = 3.6;
          }

          L.circleMarker([lat, lon], {
            radius: radius,
            color: strokeColor,
            fillColor: fillColor,
            fillOpacity: 0.85,
            weight: 0.8
          }).bindPopup(
            `🔥 <b>Foco Satelital VIIRS (375m)</b><br>` +
            `Fecha: <b>${iso_date}</b> (Semana ${wk})<br>` +
            `Potencia FRP: <b>${frp} MW</b><br>` +
            `Coordenadas: <code>[${lat.toFixed(3)}, ${lon.toFixed(3)}]</code>`
          ).addTo(AppState.calendar.cellsLayer);
        });

        const countEl = document.getElementById('cal-annual-pts-count');
        if (countEl) countEl.innerText = `${renderedPoints.toLocaleString()} focos`;

        const coordsLabel = document.getElementById('cal-box-coords-label');
        if (coordsLabel && !bounds) {
          coordsLabel.innerText = '';
        }
      } else {
        // MODO 2: INTERVALO DE TIEMPO (O SERIE COMPLETA) CON CUADRÍCULAS DE 15 KM
        const isInterval = (AppState.calendar.mode === 'interval');
        const fromY = isInterval ? AppState.calendar.rangeFrom : 2000;
        const toY = isInterval ? AppState.calendar.rangeTo : 2026;
        const numYears = Math.max(1, toY - fromY + 1);

        cells.forEach(c => {
          const inside = !bounds || bounds.contains([c.lat, c.lon]);
          let intervalEq = 0;
          let intervalFrp = 0;

          if (c.weeks) {
            for (let w = 1; w <= 52; w++) {
              const wObj = c.weeks[String(w)];
              if (wObj && wObj.by_year) {
                for (let y = fromY; y <= toY; y++) {
                  if (wObj.by_year[String(y)]) {
                    intervalEq += wObj.by_year[String(y)].eq || 0;
                    intervalFrp += wObj.by_year[String(y)].frp_mw || 0;
                  }
                }
              }
            }
          }
          const avgEq = intervalEq / numYears;

          let fillColor = '#eab308';
          let strokeColor = '#ca8a04';
          let radius = 3.5;

          if (avgEq >= 25) {
            fillColor = '#dc2626';
            strokeColor = '#991b1b';
            radius = 6.5;
          } else if (avgEq >= 8) {
            fillColor = '#f97316';
            strokeColor = '#c2410c';
            radius = 5.2;
          } else if (avgEq >= 2) {
            fillColor = '#f59e0b';
            strokeColor = '#b45309';
            radius = 4.2;
          }

          L.circleMarker([c.lat, c.lon], {
            radius: inside ? radius : 3.0,
            color: inside ? strokeColor : '#cbd5e1',
            fillColor: inside ? fillColor : '#e2e8f0',
            fillOpacity: inside ? 0.85 : 0.25,
            weight: inside ? 1.2 : 0.8
          }).bindPopup(
            `<b>${c.zone_name}</b> (${c.province})<br>` +
            `Intervalo: <b>${fromY}–${toY}</b> (${numYears} años)<br>` +
            `Focos en intervalo: <b>${Math.round(intervalEq).toLocaleString()} eq</b> (Promedio: <b>${avgEq.toFixed(1)}/año</b>)<br>` +
            `Coordenadas: <code>[${c.lat.toFixed(2)}, ${c.lon.toFixed(2)}]</code>`
          ).addTo(AppState.calendar.cellsLayer);
        });

        const coordsLabel = document.getElementById('cal-box-coords-label');
        if (coordsLabel && !bounds) {
          coordsLabel.innerText = '';
        }
      }
    }

    function renderCalendar() {
      renderCalendarCellsOnMap();
      const cells = (AppState.historicalGrid && AppState.historicalGrid.cells) || [];
      const meta = (AppState.historicalGrid && AppState.historicalGrid.metadata) || { current_year: 2026, current_closed_week: 46 };
      const bounds = AppState.calendar.selectedBounds;
      const selYear = AppState.calendar.selectedYear;

      const activeCells = bounds ? cells.filter(c => bounds.contains([c.lat, c.lon])) : cells;
      const ratioEl = document.getElementById('cal-info-ratio');
      if (ratioEl) ratioEl.innerText = `${activeCells.length} cuadrículas activas`;

      // Calcular área de la parcela
      if (bounds) {
        const sw = bounds.getSouthWest();
        const ne = bounds.getNorthEast();
        const kmLat = Math.abs(ne.lat - sw.lat) * 111.0;
        const kmLon = Math.abs(ne.lng - sw.lng) * 111.0 * Math.cos(((sw.lat + ne.lat) / 2) * Math.PI / 180);
        const areaKm2 = Math.max(1, Math.round(kmLat * kmLon));
        const coordText = `Coordenadas [${sw.lat.toFixed(2)}, ${sw.lng.toFixed(2)}] a [${ne.lat.toFixed(2)}, ${ne.lng.toFixed(2)}] (~${areaKm2.toLocaleString()} km²)`;
        const coordsLabel = document.getElementById('cal-box-coords-label');
        if (coordsLabel) coordsLabel.innerText = coordText;
        const parcelAreaEl = document.getElementById('cal-stat-parcel-area');
        if (parcelAreaEl) parcelAreaEl.innerText = coordText;
      } else {
        const parcelAreaEl = document.getElementById('cal-stat-parcel-area');
        if (parcelAreaEl) parcelAreaEl.innerText = `Región: Provincias de Córdoba y San Luis`;
      }

      const monthNames = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
      const weeksData = [];

      let totalObsEq = 0;
      let totalObsViirs = 0;
      let totalObsModis = 0;
      let totalObsFrp = 0;

      for (let w = 1; w <= 52; w++) {
        const approxMonth = monthNames[Math.min(11, Math.floor((w - 1) / 4.33))];
        const isInterval = (AppState.calendar.mode === 'interval');
        const fromY = isInterval ? AppState.calendar.rangeFrom : (selYear === 'ALL' ? 2000 : parseInt(selYear));
        const toY = isInterval ? AppState.calendar.rangeTo : (selYear === 'ALL' ? 2026 : parseInt(selYear));
        const numYears = Math.max(1, toY - fromY + 1);

        const isPending = !isInterval && (selYear !== 'ALL' && parseInt(selYear) === meta.current_year && w > meta.current_closed_week);

        // Calcular serie anual real en las celdas seleccionadas para la semana w (2000 a 2025 años cerrados)
        const yearlyTotals = {};
        for (let yr = 2000; yr <= 2025; yr++) yearlyTotals[yr] = 0;

        let obsEq = 0;
        let obsViirs = 0;
        let obsModis = 0;
        let obsFrp = 0;

        activeCells.forEach(c => {
          const wObj = c.weeks && c.weeks[String(w)];
          if (!wObj || !wObj.by_year) return;

          for (let yr = 2000; yr <= 2025; yr++) {
            if (wObj.by_year[String(yr)]) {
              yearlyTotals[yr] += wObj.by_year[String(yr)].eq || 0;
            }
          }

          if (isInterval) {
            let wSumEq = 0, wSumV = 0, wSumM = 0, wSumFrp = 0;
            for (let yr = fromY; yr <= toY; yr++) {
              if (wObj.by_year[String(yr)]) {
                wSumEq += wObj.by_year[String(yr)].eq || 0;
                wSumV += wObj.by_year[String(yr)].viirs || 0;
                wSumM += wObj.by_year[String(yr)].modis || 0;
                wSumFrp += wObj.by_year[String(yr)].frp_mw || 0;
              }
            }
            obsEq += wSumEq / numYears;
            obsViirs += wSumV / numYears;
            obsModis += wSumM / numYears;
            obsFrp += wSumFrp / numYears;
          } else if (selYear === 'ALL') {
            const yrs = Object.keys(wObj.by_year);
            yrs.forEach(yk => {
              obsEq += (wObj.by_year[yk].eq || 0) / 26.0;
              obsViirs += (wObj.by_year[yk].viirs || 0) / 26.0;
              obsModis += (wObj.by_year[yk].modis || 0) / 26.0;
              obsFrp += (wObj.by_year[yk].frp_mw || 0) / 26.0;
            });
          } else if (!isPending && wObj.by_year[selYear]) {
            obsEq += wObj.by_year[selYear].eq || 0;
            obsViirs += wObj.by_year[selYear].viirs || 0;
            obsModis += wObj.by_year[selYear].modis || 0;
            obsFrp += wObj.by_year[selYear].frp_mw || 0;
          }
        });

        const baseArr = Object.values(yearlyTotals);
        const meanVal = baseArr.reduce((a, b) => a + b, 0) / Math.max(1, baseArr.length);
        const variance = baseArr.reduce((a, b) => a + Math.pow(b - meanVal, 2), 0) / Math.max(1, baseArr.length - 1);
        const stdVal = Math.max(0.5, Math.sqrt(variance));

        let zScore = null;
        let status = 'Semana no cerrada / Sin datos aún';
        let color = '#f1f5f9';
        let textColor = '#94a3b8';
        let tier = 0;

        if (!isPending) {
          zScore = Number(((obsEq - meanVal) / stdVal).toFixed(2));
          if (obsEq <= 0.1) {
            status = 'Sin Actividad / Ventana Óptima';
            color = '#d1fae5';
            textColor = '#065f46';
            tier = 1;
          } else if (zScore >= 1.8) {
            status = 'Riesgo Histórico Extremo (Veda Total)';
            color = '#fee2e2';
            textColor = '#991b1b';
            tier = 4;
          } else if (zScore >= 0.8) {
            status = 'Riesgo Histórico Alto (Restricción)';
            color = '#ffedd5';
            textColor = '#9a3412';
            tier = 3;
          } else if (zScore >= 0.0) {
            status = 'Riesgo Moderado (Media Estacional)';
            color = '#fef3c7';
            textColor = '#92400e';
            tier = 2;
          } else {
            status = 'Riesgo Bajo (Bajo la Media)';
            color = '#d1fae5';
            textColor = '#065f46';
            tier = 1;
          }

          totalObsEq += obsEq;
          totalObsViirs += Math.round(obsViirs);
          totalObsModis += Math.round(obsModis);
          totalObsFrp += obsFrp;
        }

        weeksData.push({
          week: w,
          month: approxMonth,
          baseline_mean: Number(meanVal.toFixed(1)),
          baseline_std: Number(stdVal.toFixed(1)),
          observed_harmonized: Number(obsEq.toFixed(1)),
          observed_raw: Math.round(obsViirs + obsModis),
          observed_frp_mw: Number(obsFrp.toFixed(1)),
          z_score: zScore,
          pending: isPending,
          status,
          color,
          textColor,
          tier
        });
      }

      const isIntervalMode = (AppState.calendar.mode === 'interval');
      document.getElementById('cal-stat-harmonized-hotspots').innerText = isIntervalMode
        ? `${Math.round(totalObsEq).toLocaleString()} eq/año`
        : `${Math.round(totalObsEq).toLocaleString()} eq`;
      document.getElementById('cal-stat-raw-breakdown').innerText = isIntervalMode
        ? `${Math.round(totalObsViirs).toLocaleString()} VIIRS + ${Math.round(totalObsModis).toLocaleString()} MODIS eq/año`
        : `${totalObsViirs.toLocaleString()} VIIRS + ${totalObsModis.toLocaleString()} MODIS eq`;
      document.getElementById('cal-stat-fre').innerText = `${Math.round(totalObsFrp).toLocaleString()} MW`;
      const riskIdxEl = document.getElementById('cal-kpi-risk-index');
      if (riskIdxEl) {
        const totalArchive = (meta && meta.direct_firms_points_count) ? meta.direct_firms_points_count.toLocaleString() : '218,518';
        if (isIntervalMode) {
          riskIdxEl.innerText = `✓ Intervalo ${AppState.calendar.rangeFrom}–${AppState.calendar.rangeTo}: ${Math.round(totalObsEq).toLocaleString()} eq/año prom`;
        } else if (selYear === 'ALL') {
          riskIdxEl.innerText = `✓ ${totalArchive} focos reales NASA (2000–2026)`;
        } else {
          riskIdxEl.innerText = `✓ Año ${selYear}: ${Math.round(totalObsEq).toLocaleString()} focos reales en vista`;
        }
      }

      // Render de las 12 columnas mensuales
      const grid = document.getElementById('cal-weeks-grid');
      grid.innerHTML = '';

      for (let m = 0; m < 12; m++) {
        const monthWeeks = weeksData.filter(w => Math.min(11, Math.floor((w.week - 1) / 4.33)) === m);
        const col = document.createElement('div');
        col.className = "bg-slate-50 p-2 rounded-2xl border border-slate-200/70 flex flex-col space-y-1.5";

        const title = document.createElement('div');
        title.className = "text-[11px] font-bold text-slate-500 text-center border-b border-slate-200/70 pb-1";
        title.innerText = monthNames[m];
        col.appendChild(title);

        monthWeeks.forEach(w => {
          const cell = document.createElement('button');
          cell.dataset.week = String(w.week);
          const isSelected = (w.week === AppState.calendar.selectedWeek);
          cell.className = `week-cell-btn w-full py-1.5 px-1.5 rounded-xl text-[10px] font-bold flex items-center justify-between border transition-all ${
            isSelected ? 'border-red-600 ring-2 ring-red-400/50 shadow-sm scale-105' : 'border-slate-200/70 hover:scale-105'
          }`;
          cell.style.backgroundColor = w.color;
          cell.style.color = w.textColor || '#0f172a';
          cell.innerHTML = `<span>S${w.week}</span><span>${w.pending ? '⏳' : (w.observed_harmonized > 0 ? Math.round(w.observed_harmonized) + '🔥' : '0')}</span>`;
          cell.onclick = () => {
            AppState.calendar.selectedWeek = w.week;
            document.querySelectorAll('#cal-weeks-grid .week-cell-btn').forEach(btn => {
              if (btn.dataset.week === String(w.week)) {
                btn.classList.remove('border-slate-200/70');
                btn.classList.add('border-red-600', 'ring-2', 'ring-red-400/50', 'shadow-sm', 'scale-105');
              } else {
                btn.classList.remove('border-red-600', 'ring-2', 'ring-red-400/50', 'shadow-sm', 'scale-105');
                btn.classList.add('border-slate-200/70');
              }
            });
            showWeekDetail(w);
          };
          col.appendChild(cell);
        });

        grid.appendChild(col);
      }

      const selW = weeksData.find(w => w.week === AppState.calendar.selectedWeek) || weeksData[35];
      if (selW) showWeekDetail(selW);
    }

    function showWeekDetail(w) {
      document.getElementById('cal-stat-current-week').innerText = `Semana ${w.week}`;
      const periodLabel = (AppState.calendar.mode === 'interval')
        ? `${AppState.calendar.rangeFrom}–${AppState.calendar.rangeTo}`
        : (AppState.calendar.selectedYear === 'ALL' ? '2000–2026' : AppState.calendar.selectedYear);
      document.getElementById('cal-stat-current-month').innerText = `Mes de ${w.month} (${periodLabel})`;

      const weekFrpEl = document.getElementById('cal-stat-week-frp');
      if (weekFrpEl) {
        weekFrpEl.innerText = w.pending ? '-- MW' : `${w.observed_frp_mw.toLocaleString()} MW`;
      }

      const zEl = document.getElementById('cal-stat-zscore');
      const zDesc = document.getElementById('cal-stat-zscore-desc');

      if (w.pending || w.z_score === null) {
        zEl.innerText = 'N/A';
        zEl.className = 'text-2xl font-black text-slate-400 mt-1';
        zDesc.innerText = 'Semana aún no cerrada';
      } else {
        zEl.innerText = `${w.z_score >= 0 ? '+' : ''}${w.z_score.toFixed(2)} σ`;
        if (w.z_score >= 1.5) {
          zEl.className = 'text-2xl font-black text-red-600 mt-1';
          zDesc.innerText = 'Sobre la media histórica (Crítico)';
        } else if (w.z_score > 0.0) {
          zEl.className = 'text-2xl font-black text-amber-600 mt-1';
          zDesc.innerText = 'Actividad moderada sobre la media';
        } else {
          zEl.className = 'text-2xl font-black text-emerald-600 mt-1';
          zDesc.innerText = 'En o por debajo de la media histórica';
        }
      }
    }

    function renderSeasonalSvgChart(weeks) {
      const svg = document.getElementById('cal-seasonal-chart');
      if (!svg || !weeks.length) return;

      const maxVal = Math.max(10, ...weeks.map(w => Math.max(w.baseline_mean + w.baseline_std, w.observed_harmonized))) * 1.2;
      const width = 800;
      const height = 220;
      const padLeft = 40;
      const padBottom = 26;
      const plotW = width - padLeft - 20;
      const plotH = height - padBottom - 16;

      const upperPoints = [];
      const lowerPoints = [];
      const meanPoints = [];
      const obsCircles = [];

      weeks.forEach((w, idx) => {
        const x = padLeft + (idx / 51) * plotW;
        const yMean = 16 + plotH - (w.baseline_mean / maxVal) * plotH;
        const yUpper = 16 + plotH - (Math.min(maxVal, w.baseline_mean + w.baseline_std) / maxVal) * plotH;
        const yLower = 16 + plotH - (Math.max(0, w.baseline_mean - w.baseline_std) / maxVal) * plotH;

        meanPoints.push(`${x.toFixed(1)},${yMean.toFixed(1)}`);
        upperPoints.push(`${x.toFixed(1)},${yUpper.toFixed(1)}`);
        lowerPoints.unshift(`${x.toFixed(1)},${yLower.toFixed(1)}`);

        if (!w.pending && w.observed_harmonized > 0) {
          const yObs = 16 + plotH - (w.observed_harmonized / maxVal) * plotH;
          obsCircles.push(`<circle cx="${x.toFixed(1)}" cy="${yObs.toFixed(1)}" r="4.5" fill="#dc2626" stroke="#FFFFFF" stroke-width="1.8"/>`);
        }
      });

      svg.innerHTML = `
        <defs>
          <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0284c7" stop-opacity="0.25"/>
            <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <line x1="${padLeft}" y1="16" x2="${width - 20}" y2="16" stroke="#e2e8f0" stroke-dasharray="4,4"/>
        <line x1="${padLeft}" y1="${16 + plotH / 2}" x2="${width - 20}" y2="${16 + plotH / 2}" stroke="#e2e8f0" stroke-dasharray="4,4"/>
        <line x1="${padLeft}" y1="${16 + plotH}" x2="${width - 20}" y2="${16 + plotH}" stroke="#cbd5e1" stroke-width="1.5"/>
        <polygon points="${upperPoints.concat(lowerPoints).join(' ')}" fill="url(#bandGrad)" />
        <polyline points="${meanPoints.join(' ')}" fill="none" stroke="#0284c7" stroke-width="2.5"/>
        ${obsCircles.join('')}
        <text x="50" y="${height - 6}" fill="#64748b" font-size="11" font-weight="bold">Ene</text>
        <text x="190" y="${height - 6}" fill="#64748b" font-size="11" font-weight="bold">Abr</text>
        <text x="370" y="${height - 6}" fill="#64748b" font-size="11" font-weight="bold">Jul</text>
        <text x="530" y="${height - 6}" fill="#dc2626" font-size="11" font-weight="bold">Ago-Oct (Pico Crítico)</text>
        <text x="735" y="${height - 6}" fill="#64748b" font-size="11" font-weight="bold">Dic</text>
      `;
    }

    // =========================================================================
    // SECCIÓN 4: MAPA OPERATIVO (PESTAÑAS 2 Y 3) + MOTOR TÁCTICO Y SIMULADOR
    // =========================================================================
    function initMap() {
      const initialLat = AppState.userLocation.lat;
      const initialLon = AppState.userLocation.lon;

      map = L.map('map', {
        zoomControl: false,
        attributionControl: false,
        maxBounds: AppState.CORDOBA_SANLUIS_BOUNDS.pad(0.15),
        minZoom: 6
      }).setView([initialLat, initialLon], 11);

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      const satLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Esri World Imagery'
      }).addTo(map);

      const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: 'OpenStreetMap'
      });

      // Orden jerárquico de panes para que los puntos satelitales y vectores queden sobre los polígonos
      map.createPane('conesPane');
      map.getPane('conesPane').style.zIndex = 410;

      map.createPane('clustersPane');
      map.getPane('clustersPane').style.zIndex = 420;

      map.createPane('satellitePointsPane');
      map.getPane('satellitePointsPane').style.zIndex = 450;

      addProvinceMaskToMap(map);

      AppState.layers.projectionCones = L.featureGroup().addTo(map);
      AppState.layers.firePolygons = L.featureGroup().addTo(map);
      AppState.layers.modisPoints = L.featureGroup().addTo(map);
      AppState.layers.viirsPoints = L.featureGroup().addTo(map);
      AppState.layers.safeZones = L.featureGroup().addTo(map);
      AppState.layers.escapeRoute = L.featureGroup().addTo(map);

      L.control.layers({
        "🛰️ Satélite Esri": satLayer,
        "🗺️ Calles (OSM)": osmLayer
      }, {
        "📐 Perímetros Frentes": AppState.layers.firePolygons,
        "🧭 Conos Predictivos (1h/3h)": AppState.layers.projectionCones,
        "🟠 Focos VIIRS (375m)": AppState.layers.viirsPoints,
        "🔴 Focos MODIS (1km)": AppState.layers.modisPoints,
        "🧭 Ruta y Vector de Evacuación": AppState.layers.escapeRoute
      }, { position: 'topright' }).addTo(map);

      const userIcon = L.divIcon({
        className: 'user-pulse-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      AppState.userMarker = L.marker([initialLat, initialLon], {
        icon: userIcon,
        draggable: true
      }).addTo(map).bindPopup("<b>📍 Posición del Usuario</b><br>Arrástreme o use el botón GPS para ubicarse.");

      AppState.userMarker.on('dragend', function (e) {
        const pos = e.target.getLatLng();
        AppState.userLocation.lat = pos.lat;
        AppState.userLocation.lon = pos.lng;
        if (AppState.gpsAccuracyCircle) {
          AppState.gpsAccuracyCircle.setLatLng(pos);
        }
        recalculatePredictiveEngine();
      });

      // Botón flotante para recentrar en GPS Real
      const gpsControl = L.control({ position: 'topleft' });
      gpsControl.onAdd = function() {
        const div = L.DomUtil.create('div', 'leaflet-bar');
        const btn = L.DomUtil.create('a', '', div);
        btn.innerHTML = '📍';
        btn.href = '#';
        btn.title = 'Centrar en mi ubicación GPS real';
        btn.style.fontSize = '15px';
        btn.style.width = '34px';
        btn.style.height = '34px';
        btn.style.lineHeight = '34px';
        btn.style.textAlign = 'center';
        btn.style.backgroundColor = '#0F172A';
        btn.style.color = '#38BDF8';
        btn.style.display = 'block';
        btn.onclick = function(e) {
          L.DomEvent.preventDefault(e);
          L.DomEvent.stopPropagation(e);
          requestUserRealLocation(true);
        };
        return div;
      };
      gpsControl.addTo(map);

      map.on('click', function(e) {
        if (AppState.isInjectingFire) {
          const sevEl = document.getElementById('sim-fire-severity');
          const severity = sevEl ? sevEl.value : 'critical';
          injectSimulatedFireAt(e.latlng.lat, e.latlng.lng, severity);
          toggleInjectFireMode(false);
          return;
        }
        AppState.userLocation.lat = e.latlng.lat;
        AppState.userLocation.lon = e.latlng.lng;
        AppState.userMarker.setLatLng(e.latlng);
        if (AppState.gpsAccuracyCircle) {
          AppState.gpsAccuracyCircle.setLatLng(e.latlng);
        }
        recalculatePredictiveEngine();
      });
    }

    // =========================================================================
    // GEOLOCALIZACIÓN GPS REAL DEL DISPOSITIVO
    // =========================================================================
    function requestUserRealLocation(autoCenter = true) {
      const statusBadge = document.getElementById('gps-status-badge');
      if (!navigator.geolocation) {
        if (statusBadge) {
          statusBadge.innerText = '📍 GPS: No Soportado';
          statusBadge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200 font-bold';
        }
        return;
      }

      if (statusBadge) {
        statusBadge.innerText = '📍 GPS: Adquiriendo...';
        statusBadge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-bold animate-pulse';
      }

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          const accuracy = Math.round(pos.coords.accuracy || 20);

          AppState.userLocation.lat = lat;
          AppState.userLocation.lon = lon;
          AppState.userGpsAccuracy = accuracy;
          AppState.isRealGpsActive = true;

          if (AppState.userMarker) {
            AppState.userMarker.setLatLng([lat, lon]);
            AppState.userMarker.setPopupContent(`<b>📍 Mi Ubicación Real (GPS)</b><br>Precisión: ±${accuracy} m<br>Coordenadas: ${lat.toFixed(5)}, ${lon.toFixed(5)}`);
          }

          if (AppState.gpsAccuracyCircle) {
            AppState.gpsAccuracyCircle.setLatLng([lat, lon]).setRadius(accuracy);
          } else if (map) {
            AppState.gpsAccuracyCircle = L.circle([lat, lon], {
              radius: accuracy,
              color: '#0284C7',
              fillColor: '#38BDF8',
              fillOpacity: 0.15,
              weight: 1.5,
              dashArray: '4, 4'
            }).addTo(map);
          }

          if (statusBadge) {
            statusBadge.innerText = `📍 GPS En Vivo (±${accuracy}m)`;
            statusBadge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold';
          }

          if (autoCenter && map) {
            map.setView([lat, lon], 14);
          }

          recalculatePredictiveEngine();
        },
        (err) => {
          console.warn('[SeMF] Error o rechazo de GPS:', err);
          AppState.isRealGpsActive = false;
          if (statusBadge) {
            statusBadge.innerText = '📍 GPS: Táctico / Manual';
            statusBadge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-bold';
          }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
      );
    }

    // =========================================================================
    // FASE B: FILTRO TÁCTICO DE VENTANA DE 24 HORAS (DINÁMICO Y DESLIZANTE)
    // =========================================================================
    const TACTICAL_MAX_AGE_MS = 24 * 60 * 60 * 1000;
    const CLOCK_SKEW_TOLERANCE_MS = 2 * 60 * 60 * 1000; // 2 horas de margen para desfases UTC/reloj

    function parseSatelliteUtcMs(tsStr) {
      if (!tsStr || typeof tsStr !== 'string') return NaN;
      const clean = tsStr.trim();
      const iso = clean.includes('T')
        ? (clean.endsWith('Z') ? clean : `${clean}Z`)
        : `${clean.replace(' ', 'T')}Z`;
      return Date.parse(iso);
    }

    function getDynamicTacticalReferenceMs() {
      const clientNowMs = Date.now();
      const points = (AppState.dashboardData && Array.isArray(AppState.dashboardData.points)) ? AppState.dashboardData.points : [];
      if (!points.length) return clientNowMs;

      let latestTelemetryMs = 0;
      for (const pt of points) {
        const ms = parseSatelliteUtcMs(pt.acq_datetime);
        if (!isNaN(ms) && ms > latestTelemetryMs) latestTelemetryMs = ms;
      }

      // 1. Si el pase satelital más reciente está ligeramente adelantado al reloj local por desfase UTC:
      if (latestTelemetryMs > clientNowMs) {
        return latestTelemetryMs;
      }
      // 2. Si estamos en un dataset histórico grabado de prueba (más de 48h de antigüedad):
      if (clientNowMs - latestTelemetryMs > 48 * 3600 * 1000) {
        return latestTelemetryMs;
      }
      // 3. Operación estándar en vivo en tiempo real continuo:
      return clientNowMs;
    }

    function isWithinTactical24hWindow(tsStr) {
      const itemMs = parseSatelliteUtcMs(tsStr);
      if (isNaN(itemMs)) return false;
      const refMs = getDynamicTacticalReferenceMs();
      const ageMs = refMs - itemMs;
      // Dinámico: no más de 24h de antigüedad, tolerando hasta 2h de skew UTC
      return ageMs <= TACTICAL_MAX_AGE_MS && ageMs >= -CLOCK_SKEW_TOLERANCE_MS;
    }

    function updateTacticalWindowBadge() {
      const badge = document.getElementById('tactical-window-badge');
      if (!badge) return;
      const refMs = getDynamicTacticalReferenceMs();
      const isLive = Math.abs(Date.now() - refMs) < 60000;
      const refDate = new Date(refMs);
      const timeStr = `${String(refDate.getUTCHours()).padStart(2, '0')}:${String(refDate.getUTCMinutes()).padStart(2, '0')} UTC`;
      badge.innerText = isLive ? '⏱️ Ventana: Últimas 24h' : `⏱️ Ventana: 24h (${timeStr})`;
      badge.title = `Filtro Táctico Activo: Focos de las últimas 24 horas (Referencia: ${refDate.toISOString()})`;
    }

    function getAllTacticalEvents() {
      if (AppState.isOperationalInjectionActive) {
        return [...AppState.injectedClusters];
      }
      const rawEvents = (AppState.dashboardData && Array.isArray(AppState.dashboardData.events))
        ? AppState.dashboardData.events
        : [];
      return rawEvents.filter(ev => ev.is_simulated || isWithinTactical24hWindow(ev.last_detected));
    }

    async function selectTacticalCluster(ev, centerMap = false) {
      if (!ev) return;
      AppState.selectedCluster = ev;
      updateTacticalWindowBadge();
      renderClusterPills();
      updateClusterDisplay();
      if (!AppState.isOperationalInjectionActive && !AppState.isUsingInjectedWeather) {
        await fetchRealWeather();
      }
      recalculatePredictiveEngine();
      if (centerMap && map) {
        map.setView([ev.centroid_lat, ev.centroid_lon], 13);
      }
    }

    function getFrpColorStyle(frpMw) {
      const val = Number(frpMw) || 0;
      if (val < 50) {
        return { fill: '#FACC15', stroke: '#CA8A04' }; // Amarillo (< 50 MW)
      }
      if (val <= 200) {
        return { fill: '#FB923C', stroke: '#EA580C' }; // Naranja (50 MW a 200 MW)
      }
      if (val <= 500) {
        return { fill: '#EF4444', stroke: '#B91C1C' }; // Rojo (200 MW a 500 MW)
      }
      return { fill: '#881337', stroke: '#4C0519' };   // Rojo-Oscuro / Bordó (> 500 MW)
    }

    function loadActiveFireData() {
      const data = AppState.dashboardData;
      const events = getAllTacticalEvents();
      if ((!AppState.selectedCluster || !events.some(e => e.event_id === AppState.selectedCluster.event_id)) && events.length > 0) {
        AppState.selectedCluster = events[0];
      } else if (events.length === 0) {
        AppState.selectedCluster = null;
      }

      // Encuadre inicial inteligente: centra la cámara en el frente activo principal
      if (!AppState.isRealGpsActive && AppState.selectedCluster && !AppState._hasInitiallyCentered && map) {
        AppState._hasInitiallyCentered = true;
        const cLat = AppState.selectedCluster.centroid_lat;
        const cLon = AppState.selectedCluster.centroid_lon;
        AppState.userLocation.lat = cLat - 0.035;
        AppState.userLocation.lon = cLon;
        if (AppState.userMarker) {
          AppState.userMarker.setLatLng([AppState.userLocation.lat, AppState.userLocation.lon]);
        }
        map.setView([cLat, cLon], 11);
      }

      AppState.layers.viirsPoints.clearLayers();
      AppState.layers.modisPoints.clearLayers();

      const pointsToRender = AppState.isOperationalInjectionActive
        ? AppState.injectedPoints
        : (data && Array.isArray(data.points)
            ? data.points.filter(pt => pt.is_simulated || isWithinTactical24hWindow(pt.acq_datetime))
            : []);

      pointsToRender.forEach(pt => {
        const isViirs = pt.sensor_family === 'VIIRS';
        const simTag = pt.is_simulated ? ' [Inyectado]' : '';
        const cStyle = getFrpColorStyle(pt.frp_mw);
        const popupHtml = `
          <div style="font-family: monospace; font-size: 11px; min-width: 190px;">
            <b style="color: ${cStyle.stroke};">${isViirs ? '🟠 VIIRS 375m' : '🔴 MODIS 1km'} (${pt.satellite_name})${simTag}</b><br>
            <hr style="margin: 4px 0; border-color: #334155;">
            <b>FRP:</b> ${pt.frp_mw} MW (${pt.frp_density_mw_km2} MW/km²)<br>
            <b>Temp. Brillo (4µm):</b> ${pt.temp_ch4_k} K<br>
            <b>Anomalía ΔT:</b> ${pt.delta_temp_k} K<br>
            <b>Huella Píxel:</b> ${pt.pixel_area_km2} km²<br>
            <b>${pt.is_simulated ? 'Estado' : 'UTC'}:</b> ${pt.is_simulated ? 'Inyección Operativa' : pt.acq_datetime}
          </div>
        `;
        if (isViirs) {
          L.circleMarker([pt.latitude, pt.longitude], {
            pane: 'satellitePointsPane',
            radius: pt.is_simulated ? 5.5 : 4.5,
            color: cStyle.stroke,
            fillColor: cStyle.fill,
            fillOpacity: pt.is_simulated ? 0.92 : 0.88,
            weight: pt.is_simulated ? 2 : 1.5
          }).bindPopup(popupHtml).addTo(AppState.layers.viirsPoints);
        } else {
          L.circleMarker([pt.latitude, pt.longitude], {
            pane: 'satellitePointsPane',
            radius: pt.is_simulated ? 8.5 : 7.5,
            color: cStyle.stroke,
            fillColor: cStyle.fill,
            fillOpacity: pt.is_simulated ? 0.85 : 0.78,
            weight: 2
          }).bindPopup(popupHtml).addTo(AppState.layers.modisPoints);
        }
      });

      updateTacticalWindowBadge();
      renderClusterPills();
      updateClusterDisplay();
    }

    function renderClusterPills() {
      const events = getAllTacticalEvents();
      const brigadeContainer = document.getElementById('brigade-cluster-pills');
      brigadeContainer.innerHTML = '';
      if (!events.length) {
        brigadeContainer.innerHTML = '<span class="text-[11px] text-emerald-700 font-semibold italic">Sin frentes activos en las últimas 24 h.</span>';
        return;
      }
      events.forEach(ev => {
        const isSel = AppState.selectedCluster && AppState.selectedCluster.event_id === ev.event_id;
        const pill = document.createElement('button');
        pill.className = `px-2.5 py-1 rounded-full text-[10px] whitespace-nowrap border transition ${
          isSel ? 'bg-red-600 text-white border-red-600 font-bold shadow-sm' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100 font-medium'
        }`;
        pill.innerText = `${ev.event_id} (${Math.round(ev.frp_peak_mw || 0)} MW)`;
        pill.onclick = () => selectTacticalCluster(ev, true);
        brigadeContainer.appendChild(pill);
      });
    }

    function updateClusterDisplay() {
      if (!AppState.selectedCluster) {
        document.getElementById('brigade-selected-cluster').innerText = '--';
        document.getElementById('brigade-location-name').innerText = 'Sin frente seleccionado';
        document.getElementById('brigade-area').innerText = '-- ha';
        document.getElementById('hud-frp').innerText = '-- MW';
        return;
      }
      const c = AppState.selectedCluster;
      document.getElementById('brigade-selected-cluster').innerText = c.event_id;
      document.getElementById('brigade-location-name').innerText = c.location_name || 'Sierras de Córdoba y San Luis';
      document.getElementById('brigade-area').innerText = `${c.detection_area_ha} ha`;
      document.getElementById('hud-frp').innerText = `${c.frp_peak_mw || 150} MW`;
    }

    // =========================================================================
    // SECCIÓN 5: CLIMA REAL OPEN-METEO Y CONTROLES DEL SIMULADOR INYECTADO
    // =========================================================================
    async function fetchRealWeather() {
      if (AppState.isOperationalInjectionActive || AppState.isUsingInjectedWeather) return;
      if (!AppState.selectedCluster) return;
      const lat = AppState.selectedCluster.centroid_lat;
      const lon = AppState.selectedCluster.centroid_lon;

      try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m`;
        const res = await fetch(url);
        if (res.ok) {
          const d = await res.json();
          if (d && d.current) {
            AppState.weather.windSpeedKmh = d.current.wind_speed_10m ?? 28.0;
            AppState.weather.windDirectionDeg = d.current.wind_direction_10m ?? 205.0;
            AppState.weather.temperatureC = d.current.temperature_2m ?? 31.0;
            AppState.weather.relativeHumidity = d.current.relative_humidity_2m ?? 22.0;
            syncSimulatorSlidersFromWeather();
          }
        }
      } catch (err) {
        console.warn("Clima respaldo:", err);
      }
      updateHudDisplay();
    }

    function syncSimulatorSlidersFromWeather() {
      const w = AppState.weather;
      document.getElementById('sim-slider-wind-speed').value = Math.round(w.windSpeedKmh);
      document.getElementById('sim-slider-wind-dir').value = Math.round(w.windDirectionDeg);
      document.getElementById('sim-slider-temp').value = Math.round(w.temperatureC);
      document.getElementById('sim-slider-rh').value = Math.round(w.relativeHumidity);
      updateSimulatorLabels();
    }

    function updateSimulatorLabels() {
      const w = AppState.weather;
      const pushDir = (w.windDirectionDeg + 180) % 360;
      document.getElementById('sim-lbl-wind-speed').innerText = `${Math.round(w.windSpeedKmh)} km/h`;
      document.getElementById('sim-lbl-wind-dir').innerText = `${Math.round(w.windDirectionDeg)}° (Avance → ${degreesToCardinal(pushDir)})`;
      document.getElementById('sim-lbl-temp').innerText = `${Math.round(w.temperatureC)}°C`;
      document.getElementById('sim-lbl-rh').innerText = `${Math.round(w.relativeHumidity)}%`;
    }

    function onSimulatorSliderChange() {
      AppState.isUsingInjectedWeather = true;
      AppState.weather.windSpeedKmh = parseFloat(document.getElementById('sim-slider-wind-speed').value);
      AppState.weather.windDirectionDeg = parseFloat(document.getElementById('sim-slider-wind-dir').value);
      AppState.weather.temperatureC = parseFloat(document.getElementById('sim-slider-temp').value);
      AppState.weather.relativeHumidity = parseFloat(document.getElementById('sim-slider-rh').value);

      const badge = document.getElementById('hud-telemetry-mode');
      badge.innerText = '🧪 Simulador Táctico Activo';
      badge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-bold';

      updateSimulatorLabels();
      updateHudDisplay();
      recalculatePredictiveEngine();
    }

    function updateInjectedCounter() {
      const el = document.getElementById('lbl-injected-count');
      if (el) el.innerText = AppState.injectedClusters.length;
    }

    function clearAllInjectedFires() {
      AppState.injectedClusters = [];
      AppState.injectedPoints = [];
      AppState.selectedCluster = null;
      updateInjectedCounter();
      toggleInjectFireMode(false);
      loadActiveFireData();
      recalculatePredictiveEngine();
    }

    function injectQuickThreatScenario() {
      if (!AppState.isOperationalInjectionActive) {
        const toggle = document.getElementById('toggle-operational-injection');
        if (toggle) {
          toggle.checked = true;
          toggleOperationalInjection(true);
        }
      }
      const uPt = turf.point([AppState.userLocation.lon, AppState.userLocation.lat]);
      // Colocar foco a 2.5 km a barlovento (de donde proviene el viento)
      const upwindDeg = (AppState.weather.windDirectionDeg) % 360;
      const threatPt = turf.transformTranslate(uPt, 2.5, upwindDeg);
      const coords = threatPt.geometry.coordinates;
      injectSimulatedFireAt(coords[1], coords[0], 'critical');
      if (map) map.setView([AppState.userLocation.lat, AppState.userLocation.lon], 13);
    }

    function toggleInjectFireMode(force) {
      AppState.isInjectingFire = typeof force === 'boolean' ? force : !AppState.isInjectingFire;
      const btnText = document.getElementById('btn-inject-fire-text');
      const banner = document.getElementById('inject-fire-banner');
      const container = map ? map.getContainer() : null;
      if (AppState.isInjectingFire) {
        if (btnText) btnText.innerText = 'Click en Mapa...';
        if (banner) banner.classList.remove('hidden');
        if (container) container.classList.add('crosshair-cursor');
      } else {
        if (btnText) btnText.innerText = 'Plantar en Mapa';
        if (banner) banner.classList.add('hidden');
        if (container) container.classList.remove('crosshair-cursor');
      }
    }

    async function toggleOperationalInjection(enabled) {
      const panelBody = document.getElementById('injection-panel-body');
      const sosBtn = document.getElementById('btn-pedir-auxilio');

      AppState.isOperationalInjectionActive = !!enabled;

      if (enabled) {
        if (panelBody) panelBody.classList.remove('hidden');
        if (sosBtn) {
          sosBtn.disabled = true;
          sosBtn.classList.add('opacity-40', 'cursor-not-allowed');
          sosBtn.classList.remove('hover:bg-red-700', 'active:scale-95');
          sosBtn.title = 'Deshabilitado mientras Inyección Operativa está activa';
        }

        AppState.isUsingInjectedWeather = true;
        if (AppState.injectedClusters.length === 0) {
          const center = map ? map.getCenter() : { lat: -32.25, lng: -65.05 };
          const sevEl = document.getElementById('sim-fire-severity');
          const severity = sevEl ? sevEl.value : 'critical';
          injectSimulatedFireAt(center.lat, center.lng, severity);
        } else {
          AppState.selectedCluster = AppState.injectedClusters[0];
          loadActiveFireData();
        }
        onSimulatorSliderChange();
      } else {
        if (panelBody) panelBody.classList.add('hidden');
        if (sosBtn) {
          sosBtn.disabled = false;
          sosBtn.classList.remove('opacity-40', 'cursor-not-allowed');
          sosBtn.classList.add('hover:bg-red-700', 'active:scale-95');
          sosBtn.title = '';
        }

        toggleInjectFireMode(false);
        await restoreLiveTelemetry();
      }
    }

    function injectSimulatedFireAt(lat, lon, severity = 'critical') {
      const idx = AppState.injectedClusters.length + 1;
      let d = 0.012; // ~1.3 km
      let areaHa = 380.0;
      let frpMw = 350.0;
      let sevLabel = 'Crítica (Inyección)';

      if (severity === 'moderate') {
        d = 0.007;
        areaHa = 140.0;
        frpMw = 120.0;
        sevLabel = 'Moderada (Inyección)';
      } else if (severity === 'catastrophic') {
        d = 0.022;
        areaHa = 920.0;
        frpMw = 750.0;
        sevLabel = 'Catastrófica (Inyección)';
      }

      const poly = [
        [lat + d, lon - d],
        [lat + d * 1.2, lon + d * 0.4],
        [lat, lon + d * 1.3],
        [lat - d * 1.1, lon + d * 0.5],
        [lat - d, lon - d * 0.9],
        [lat + d, lon - d]
      ];
      const pushAz = (AppState.weather.windDirectionDeg + 180) % 360;
      const simCluster = {
        event_id: `INJ_FIRE_00${idx}`,
        is_simulated: true,
        event_type: 'Frente Inyectado (SeMF Simulado)',
        location_name: `Foco Inyectado #${idx} (${lat.toFixed(3)}, ${lon.toFixed(3)})`,
        centroid_lat: lat,
        centroid_lon: lon,
        points_count: 2,
        detection_area_ha: areaHa,
        frp_peak_mw: frpMw,
        spread_vector_km: 1.75,
        spread_speed_kmh: 1.75,
        spread_azimuth_deg: pushAz,
        spread_cardinal: degreesToCardinal(pushAz),
        last_detected: new Date().toISOString().slice(0, 19).replace('T', ' '),
        severity_level: sevLabel,
        satellites_involved: 'VIIRS (NOAA-21) + MODIS (Aqua)',
        polygon_coords: poly
      };
      AppState.injectedClusters.unshift(simCluster);
      AppState.selectedCluster = simCluster;

      // Puntos satelitales térmicos inyectados
      const vPt = {
        sensor_family: 'VIIRS',
        is_simulated: true,
        latitude: lat + d * 0.25,
        longitude: lon - d * 0.2,
        satellite_name: 'NOAA-21',
        frp_mw: frpMw * 0.55,
        frp_density_mw_km2: (frpMw * 0.55) / 0.14,
        temp_ch4_k: 368.5,
        delta_temp_k: 46.2,
        pixel_area_km2: 0.14
      };
      const mPt = {
        sensor_family: 'MODIS',
        is_simulated: true,
        latitude: lat - d * 0.25,
        longitude: lon + d * 0.25,
        satellite_name: 'Aqua',
        frp_mw: frpMw * 0.45,
        frp_density_mw_km2: frpMw * 0.45,
        temp_ch4_k: 345.2,
        delta_temp_k: 38.1,
        pixel_area_km2: 1.0
      };
      AppState.injectedPoints.push(vPt, mPt);

      updateInjectedCounter();
      loadActiveFireData();
      recalculatePredictiveEngine();
    }

    async function restoreLiveTelemetry() {
      AppState.isOperationalInjectionActive = false;
      AppState.isUsingInjectedWeather = false;
      AppState.injectedClusters = [];
      AppState.injectedPoints = [];
      updateInjectedCounter();
      const baseEvents = getAllTacticalEvents();
      AppState.selectedCluster = baseEvents[0] || null;

      const badge = document.getElementById('hud-telemetry-mode');
      if (badge) {
        badge.innerText = '🛰️ Clima Real Open-Meteo';
        badge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold';
      }

      loadActiveFireData();
      await fetchRealWeather();
      recalculatePredictiveEngine();
    }

    function updateHudDisplay() {
      const w = AppState.weather;
      document.getElementById('hud-wind-speed').innerText = `${Math.round(w.windSpeedKmh)} km/h`;
      document.getElementById('hud-wind-dir').innerText = `${Math.round(w.windDirectionDeg)}°`;
      document.getElementById('hud-temp').innerText = `${Math.round(w.temperatureC)}°C`;
      document.getElementById('hud-humidity').innerText = `${Math.round(w.relativeHumidity)}%`;

      const pushAzimuth = (w.windDirectionDeg + 180) % 360;
      document.getElementById('hud-wind-arrow').style.transform = `rotate(${pushAzimuth}deg)`;

      const is303030 = (w.temperatureC >= 30 && w.windSpeedKmh >= 30 && w.relativeHumidity <= 30);
      document.getElementById('badge-crossover').classList.toggle('hidden', !is303030);
    }

    // =========================================================================
    // SECCIÓN 6: MOTOR PREDICTIVO (FASE A FLECHAS, FASE B 24H, FASE C CONOS/OSRM)
    // =========================================================================
    function getClusterRadiusKm(ev) {
      let maxRadiusKm = 1.6;
      if (ev && Array.isArray(ev.polygon_coords)) {
        const cPt = turf.point([ev.centroid_lon, ev.centroid_lat]);
        ev.polygon_coords.forEach(c => {
          const d = turf.distance(cPt, turf.point([c[1], c[0]]));
          if (d > maxRadiusKm) maxRadiusKm = d;
        });
      }
      return maxRadiusKm;
    }

    function recalculatePredictiveEngine() {
      if (!map) return;

      AppState.routeRequestSeq = (AppState.routeRequestSeq || 0) + 1;
      AppState.layers.firePolygons.clearLayers();
      AppState.layers.projectionCones.clearLayers();
      AppState.layers.safeZones.clearLayers();
      AppState.layers.escapeRoute.clearLayers();

      const events = getAllTacticalEvents();
      if (!events.length) {
        const banner = document.getElementById('fsm-banner');
        const fsmIcon = document.getElementById('fsm-icon');
        const title = document.getElementById('fsm-status-title');
        const desc = document.getElementById('fsm-status-desc');
        const etaDisplay = document.getElementById('fsm-eta-display');
        if (banner) {
          banner.className = "bg-gradient-to-r from-emerald-700 to-teal-800 text-white px-4 py-2 border-b border-emerald-600/50 flex items-center justify-between shrink-0 shadow-xl";
        }
        if (fsmIcon) {
          fsmIcon.innerText = "🛡️";
          fsmIcon.className = "text-2xl";
        }
        if (title) title.innerText = "🛡️ ZONA SEGURA — SIN FOCOS ACTIVOS (<24H)";
        if (desc) desc.innerText = "Sin focos satelitales detectados en las últimas 24 horas. Monitoreo preventivo activo.";
        if (etaDisplay) etaDisplay.innerText = "ZONA SEGURA";
        const needle = document.getElementById('escape-compass-needle');
        const bearingLabel = document.getElementById('escape-bearing-label');
        const statusBadge = document.getElementById('escape-status-badge');
        const subtext = document.getElementById('escape-subtext');
        const fsmArrow = document.getElementById('fsm-bearing-arrow');
        const fsmBearingText = document.getElementById('fsm-bearing-text');
        if (needle) { needle.innerText = '🛡️'; needle.style.transform = 'rotate(0deg)'; }
        if (bearingLabel) bearingLabel.innerText = "Sin Focos Activos";
        if (statusBadge) {
          statusBadge.innerText = "🛡️ Seguro";
          statusBadge.className = "text-[9px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
        }
        if (subtext) subtext.innerText = "Monitoreo preventivo activo";
        if (fsmArrow) { fsmArrow.innerText = '🛡️'; fsmArrow.style.transform = 'rotate(0deg)'; }
        if (fsmBearingText) fsmBearingText.innerText = "SEGURO";
        document.getElementById('brigade-sat-speed').innerText = '-- km/h';
        document.getElementById('brigade-spread-dir').innerText = '--';
        AppState.currentSafeZoneTarget = null;
        return;
      }

      const w = AppState.weather;
      const windPushDir = (w.windDirectionDeg + 180) % 360;
      const hrFactor = Math.max(0.6, 1.0 + (30.0 - w.relativeHumidity) / 100.0);
      const windInducedSpeedKmh = (0.10 * w.windSpeedKmh) * hrFactor;
      const uPt = turf.point([AppState.userLocation.lon, AppState.userLocation.lat]);

      let nearestCluster = null;
      let minDistanceToUser = 999999;
      let threateningCluster = null;
      let threateningDist = 999999;

      events.forEach((ev) => {
        if (!ev.polygon_coords || ev.polygon_coords.length < 3) return;

        const latLngs = ev.polygon_coords;
        const turfCoords = latLngs.map(p => [p[1], p[0]]);

        L.polygon(latLngs, {
          pane: 'clustersPane',
          color: '#DC2626',
          weight: 2.5,
          fillColor: '#EF4444',
          fillOpacity: 0.55
        }).bindPopup(`<b>🔥 ${ev.event_id}</b><br><b>Zona:</b> ${ev.location_name || 'Sierras de Córdoba y San Luis'}<br>Severidad: ${ev.severity_level}<br>Área: ${ev.detection_area_ha} ha<br>FRP Pico: ${ev.frp_peak_mw} MW`)
          .on('click', () => selectTacticalCluster(ev, false))
          .addTo(AppState.layers.firePolygons);

        const satSpeed = ev.spread_speed_kmh || 0.0;
        const projSpeedKmh = satSpeed > 0 ? (0.4 * satSpeed + 0.6 * windInducedSpeedKmh) : windInducedSpeedKmh;
        const projAzimuth = windPushDir;
        ev.projSpeedKmh = projSpeedKmh;
        ev.projAzimuth = projAzimuth;

        // FASE C: Generación de conos Turf.js e intersección espacial booleanPointInPolygon
        let originalPoly = null;
        let cone1h = null;
        let cone3h = null;
        try {
          const ring = [...turfCoords];
          if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
            ring.push([ring[0][0], ring[0][1]]);
          }
          if (ring.length >= 4) {
            originalPoly = turf.polygon([ring]);
            cone1h = generateProjectionCone(originalPoly, projAzimuth, Math.max(0.5, projSpeedKmh * 1.0));
            cone3h = generateProjectionCone(originalPoly, projAzimuth, Math.max(1.2, projSpeedKmh * 2.5));
          }
        } catch (e) {}

        ev._originalPoly = originalPoly;
        ev._cone1h = cone1h;
        ev._cone3h = cone3h;

        const inPerimeter = originalPoly ? turf.booleanPointInPolygon(uPt, originalPoly) : false;
        const inCone1h = cone1h ? turf.booleanPointInPolygon(uPt, cone1h) : false;
        const inCone3h = cone3h ? turf.booleanPointInPolygon(uPt, cone3h) : false;

        ev._inPerimeter = inPerimeter;
        ev._inCone1h = inCone1h;
        ev._inCone3h = inCone3h;
        ev._inRedZone = (inPerimeter || inCone1h);
        ev._inOrangeZone = (!ev._inRedZone && inCone3h);
        ev._inAnyRiskCone = (inPerimeter || inCone1h || inCone3h);

        const isSelectedCluster = AppState.selectedCluster && ev.event_id === AppState.selectedCluster.event_id;
        if (isSelectedCluster || ev._inAnyRiskCone) {
          if (cone3h) {
            L.geoJSON(cone3h, {
              pane: 'conesPane',
              style: { color: '#F59E0B', weight: 1.5, dashArray: '4, 6', fillColor: '#FBBF24', fillOpacity: 0.14 }
            }).bindPopup(`<b>Cono Predictivo 3h (${ev.event_id})</b><br>Avance: ${projSpeedKmh.toFixed(2)} km/h hacia ${degreesToCardinal(projAzimuth)}`)
              .addTo(AppState.layers.projectionCones);
          }
          if (cone1h) {
            L.geoJSON(cone1h, {
              pane: 'conesPane',
              style: { color: '#F97316', weight: 2, dashArray: '5, 5', fillColor: '#FB923C', fillOpacity: 0.28 }
            }).bindPopup(`<b>Cono Predictivo 1h (${ev.event_id})</b><br>Avance: ${projSpeedKmh.toFixed(2)} km/h hacia ${degreesToCardinal(projAzimuth)}`)
              .addTo(AppState.layers.projectionCones);
          }
        }

        const dist = turf.distance(uPt, turf.point([ev.centroid_lon, ev.centroid_lat]));
        if (dist < minDistanceToUser) {
          minDistanceToUser = dist;
          nearestCluster = ev;
        }
        if (ev._inAnyRiskCone) {
          const replacesPrev = !threateningCluster ||
            (ev._inRedZone && !threateningCluster._inRedZone) ||
            ((ev._inRedZone === threateningCluster._inRedZone) && dist < threateningDist);
          if (replacesPrev) {
            threateningCluster = ev;
            threateningDist = dist;
          }
        }
      });

      const activeKinematicCluster = threateningCluster || AppState.selectedCluster || nearestCluster;
      if (activeKinematicCluster) {
        const spd = activeKinematicCluster.projSpeedKmh ?? windInducedSpeedKmh;
        const az = activeKinematicCluster.projAzimuth ?? windPushDir;
        document.getElementById('brigade-sat-speed').innerText = `${spd.toFixed(2)} km/h`;
        document.getElementById('brigade-spread-dir').innerText = `${degreesToCardinal(az)} (${Math.round(az)}°)`;
      }

      const evalCluster = threateningCluster || nearestCluster;
      const evalDist = threateningCluster ? threateningDist : minDistanceToUser;
      if (evalCluster) {
        computeSurvivalStateAndSafeZones(evalCluster, evalDist, events);
      } else {
        AppState.layers.safeZones.clearLayers();
        AppState.layers.escapeRoute.clearLayers();
        AppState.currentSafeZoneTarget = null;
      }
    }

    function generateProjectionCone(turfPoly, azimuthDeg, distanceKm) {
      if (distanceKm < 0.15) return null;
      const pts = turf.explode(turfPoly).features;
      const translated = [];
      pts.forEach(p => {
        translated.push(p);
        translated.push(turf.transformTranslate(p, distanceKm, azimuthDeg));
        translated.push(turf.transformTranslate(p, distanceKm * 0.85, (azimuthDeg - 22.5 + 360) % 360));
        translated.push(turf.transformTranslate(p, distanceKm * 0.85, (azimuthDeg + 22.5) % 360));
      });
      return turf.convex(turf.featureCollection(translated));
    }

    // =========================================================================
    // RED GEORREFERENCIADA DE REFUGIOS Y PUNTOS DE ENCUENTRO OFICIALES
    // =========================================================================
    const SAFE_SHELTER_HUBS = [
      // San Luis
      { name: "El Trapiche Centro / Balneario", lat: -33.1095, lon: -66.0640, road: "Ruta Prov. 9" },
      { name: "La Florida / Dique", lat: -33.1180, lon: -65.9870, road: "Ruta Prov. 39" },
      { name: "Potrero de los Funes Centro", lat: -33.2250, lon: -66.2300, road: "Ruta Prov. 18" },
      { name: "San Luis Capital (Autopista)", lat: -33.2980, lon: -66.3350, road: "Autopista 25 de Mayo" },
      { name: "Villa de Merlo Centro", lat: -32.3420, lon: -65.0120, road: "Ruta Nac. 148" },

      // Córdoba - Traslasierra
      { name: "Mina Clavero Centro", lat: -31.7250, lon: -65.0060, road: "Ruta Prov. 14" },
      { name: "Villa Cura Brochero (Plaza)", lat: -31.7140, lon: -65.0180, road: "Ruta Prov. 15" },
      { name: "Nono Centro", lat: -31.7980, lon: -64.9980, road: "Ruta Prov. 14" },

      // Córdoba - Sierras Chicas / Punilla / Centro
      { name: "Villa Carlos Paz (Autopista)", lat: -31.4240, lon: -64.4980, road: "RN20 / Autopista" },
      { name: "Cosquín Centro", lat: -31.2460, lon: -64.4650, road: "Ruta Nac. 38" },
      { name: "La Calera Centro", lat: -31.3440, lon: -64.3350, road: "Ruta Prov. E-55" },
      { name: "Alta Gracia Centro", lat: -31.6520, lon: -64.4280, road: "Ruta Prov. 5" }
    ];

    function isPointInsideAnyRiskCone(pt, allEvents) {
      if (!Array.isArray(allEvents)) return false;
      return allEvents.some(ev => {
        const inOrig = ev._originalPoly ? turf.booleanPointInPolygon(pt, ev._originalPoly) : false;
        const inC3 = ev._cone3h ? turf.booleanPointInPolygon(pt, ev._cone3h) : false;
        const inC1 = ev._cone1h ? turf.booleanPointInPolygon(pt, ev._cone1h) : false;
        return inOrig || inC3 || inC1;
      });
    }

    function calcSafeEscapeAzimuth(uPt, cluster) {
      const fPt = turf.point([cluster.centroid_lon, cluster.centroid_lat]);
      const radialBearing = (turf.bearing(fPt, uPt) + 360) % 360;
      const advanceAzimuth = (cluster.projAzimuth !== undefined && cluster.projAzimuth !== null)
        ? cluster.projAzimuth
        : radialBearing;

      // Ángulo relativo entre el vector de avance del fuego y la posición del usuario
      let relDiff = (radialBearing - advanceAzimuth + 360) % 360;
      if (relDiff > 180) relDiff -= 360; // entre -180 y +180

      // Si el usuario está en el eje frontal del avance (|relDiff| <= 65°):
      // Regla de Oro Forestal: escapar por el flanco lateral más cercano (perpendicular a la cabeza)
      if (Math.abs(relDiff) <= 65) {
        if (relDiff >= 0) {
          return (advanceAzimuth + 80) % 360; // Flanco derecho
        } else {
          return (advanceAzimuth - 80 + 360) % 360; // Flanco izquierdo
        }
      }
      // Si el usuario ya está en los flancos o a espaldas del fuego, huir en dirección radial alejándose del centroide
      return radialBearing;
    }

    function computeSurvivalStateAndSafeZones(cluster, distToFireKm, allEvents = []) {
      const uPt = turf.point([AppState.userLocation.lon, AppState.userLocation.lat]);
      const fPt = turf.point([cluster.centroid_lon, cluster.centroid_lat]);

      const inPerimeter = cluster._originalPoly ? turf.booleanPointInPolygon(uPt, cluster._originalPoly) : false;
      const inCone1h = cluster._cone1h ? turf.booleanPointInPolygon(uPt, cluster._cone1h) : false;
      const inCone3h = cluster._cone3h ? turf.booleanPointInPolygon(uPt, cluster._cone3h) : false;
      const isInsidePropagationCone = Boolean(inPerimeter || inCone1h || inCone3h);

      const banner = document.getElementById('fsm-banner');
      const fsmIcon = document.getElementById('fsm-icon');
      const title = document.getElementById('fsm-status-title');
      const desc = document.getElementById('fsm-status-desc');
      const etaDisplay = document.getElementById('fsm-eta-display');

      // REGLA ESTRICTA: Si no intersecta el cono de propagación (Turf.js), PROHIBIDO mostrar ruta de escape
      if (!isInsidePropagationCone) {
        banner.className = "bg-gradient-to-r from-emerald-700 to-teal-800 text-white px-4 py-2 border-b border-emerald-600/50 flex items-center justify-between shrink-0 shadow-xl";
        if (fsmIcon) {
          fsmIcon.innerText = "🛡️";
          fsmIcon.className = "text-2xl";
        }
        title.innerText = "🛡️ ZONA SEGURA — FUERA DE PELIGRO";
        desc.innerText = `Su ubicación no intersecta ningún cono de propagación activo (${distToFireKm.toFixed(1)} km al frente más cercano). No se requiere evacuación.`;
        etaDisplay.innerText = "ZONA SEGURA";

        const needle = document.getElementById('escape-compass-needle');
        const bearingLabel = document.getElementById('escape-bearing-label');
        const statusBadge = document.getElementById('escape-status-badge');
        const subtext = document.getElementById('escape-subtext');
        const fsmArrow = document.getElementById('fsm-bearing-arrow');
        const fsmBearingText = document.getElementById('fsm-bearing-text');

        if (needle) {
          needle.style.transform = 'rotate(0deg)';
          needle.innerText = '🛡️';
        }
        if (bearingLabel) bearingLabel.innerText = "Zona Despejada";
        if (statusBadge) {
          statusBadge.innerText = "🛡️ Seguro";
          statusBadge.className = "text-[9px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
        }
        if (subtext) subtext.innerText = "Sin necesidad de evacuación";
        if (fsmArrow) {
          fsmArrow.innerText = '🛡️';
          fsmArrow.style.transform = 'rotate(0deg)';
        }
        if (fsmBearingText) fsmBearingText.innerText = "SEGURO";

        AppState.layers.safeZones.clearLayers();
        AppState.layers.escapeRoute.clearLayers();
        AppState.currentSafeZoneTarget = null;
        return;
      }

      // Rumbo seguro de escape calculado por flanco/alejamiento radial
      const escapeAzimuth = calcSafeEscapeAzimuth(uPt, cluster);
      const escapeCardinal = degreesToCardinal(escapeAzimuth);

      const needle = document.getElementById('escape-compass-needle');
      const bearingLabel = document.getElementById('escape-bearing-label');
      const statusBadge = document.getElementById('escape-status-badge');
      const subtext = document.getElementById('escape-subtext');
      const fsmArrow = document.getElementById('fsm-bearing-arrow');
      const fsmBearingText = document.getElementById('fsm-bearing-text');

      if (needle) {
        needle.innerText = '▲';
        needle.style.transform = `rotate(${escapeAzimuth}deg)`;
      }
      if (bearingLabel) bearingLabel.innerText = `${escapeCardinal} · ${Math.round(escapeAzimuth)}°`;
      if (statusBadge) {
        statusBadge.innerText = "⚠️ Calculando...";
        statusBadge.className = "text-[9px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse";
      }
      if (subtext) subtext.innerText = `Evaluando viabilidad de ruta hacia flanco seguro...`;
      if (fsmArrow) {
        fsmArrow.innerText = '▲';
        fsmArrow.style.transform = `rotate(${escapeAzimuth}deg)`;
      }
      if (fsmBearingText) fsmBearingText.innerText = `${escapeCardinal} (${Math.round(escapeAzimuth)}°)`;

      const bearing = (turf.bearing(fPt, uPt) + 360) % 360;
      let deltaAngle = Math.abs(bearing - cluster.projAzimuth);
      if (deltaAngle > 180) deltaAngle = 360 - deltaAngle;

      const projSpeed = Math.max(0.3, cluster.projSpeedKmh || 0.8);
      const effectiveSpeed = Math.max(projSpeed * 0.6, projSpeed * Math.cos(deltaAngle * Math.PI / 180));
      const etaMinutes = inPerimeter
        ? 0
        : Math.max(5, Math.min(180, Math.round((Math.max(0.3, distToFireKm * 0.45) / effectiveSpeed) * 60)));

      if (inPerimeter || inCone1h) {
        banner.className = "bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white px-4 py-2 border-b border-red-500/50 flex items-center justify-between shrink-0 shadow-xl animate-pulse";
        if (fsmIcon) {
          fsmIcon.innerText = "🚨";
          fsmIcon.className = "text-2xl animate-bounce";
        }
        title.innerText = `🚨 ALERTA ROJA: IMPACTO INMINENTE — HUIR RUMBO ${escapeCardinal}`;
        desc.innerText = `Ubicación dentro de zona crítica (${cluster.event_id}). Evacúe rumbo ${escapeCardinal} (${Math.round(escapeAzimuth)}°) hacia terreno seguro.`;
        etaDisplay.innerText = inPerimeter ? "EN FOCO" : `${etaMinutes} MIN`;
      } else {
        banner.className = "bg-gradient-to-r from-amber-600 to-orange-600 text-white px-4 py-2 border-b border-amber-500/50 flex items-center justify-between shrink-0 shadow-xl";
        if (fsmIcon) {
          fsmIcon.innerText = "⚠️";
          fsmIcon.className = "text-2xl";
        }
        title.innerText = `⚠️ PRE-ALERTA: EN CONO DE AVANCE — RUMBO ${escapeCardinal}`;
        desc.innerText = `Ubicación dentro del cono a 3h (${cluster.event_id}, ${distToFireKm.toFixed(1)} km). Prepare salida rumbo ${escapeCardinal} (${Math.round(escapeAzimuth)}°).`;
        etaDisplay.innerText = `${etaMinutes} MIN`;
      }

      // SELECCIÓN SEGURA DE REFUGIO GARANTIZADO (>12 km de cualquier foco de fuego y fuera de conos)
      let bestHub = null;
      let minHubDist = 999999;

      SAFE_SHELTER_HUBS.forEach(hub => {
        const hubPt = turf.point([hub.lon, hub.lat]);
        if (isPointInsideAnyRiskCone(hubPt, allEvents)) return;

        // Distancia a todos los incendios: debe estar al menos a 12 km de cualquier centroide
        let isTooCloseToFire = false;
        for (const ev of allEvents) {
          const dFireHub = turf.distance(hubPt, turf.point([ev.centroid_lon, ev.centroid_lat]));
          if (dFireHub < 12.0) {
            isTooCloseToFire = true;
            break;
          }
        }
        if (isTooCloseToFire) return;

        const distUserToHub = turf.distance(uPt, hubPt);
        const bearingUserToHub = (turf.bearing(uPt, hubPt) + 360) % 360;
        let deltaEscape = Math.abs(bearingUserToHub - escapeAzimuth);
        if (deltaEscape > 180) deltaEscape = 360 - deltaEscape;

        // El refugio debe alinearse con la dirección segura de evacuación (<= 95°)
        if (deltaEscape <= 95 && distUserToHub < minHubDist) {
          minHubDist = distUserToHub;
          bestHub = hub;
        }
      });

      let safeLat, safeLon, safeName, safeRoad;
      if (bestHub && minHubDist < 40.0) {
        safeLat = bestHub.lat;
        safeLon = bestHub.lon;
        safeName = bestHub.name;
        safeRoad = bestHub.road;
      } else {
        // Fallback táctico: proyectar punto a 4.0 km alejándose hacia el flanco seguro (NUNCA hacia el fuego)
        let safePt = turf.transformTranslate(uPt, 4.0, escapeAzimuth);
        if (isPointInsideAnyRiskCone(safePt, allEvents)) {
          safePt = turf.transformTranslate(uPt, 6.0, (escapeAzimuth + 35) % 360);
        }
        const coords = safePt.geometry.coordinates;
        safeLat = coords[1];
        safeLon = coords[0];
        safeName = `Zona Segura de Flanco (${escapeCardinal})`;
        safeRoad = "Corredor Táctico de Salida";
      }

      AppState.currentSafeZoneTarget = { lat: safeLat, lon: safeLon, name: safeName, road: safeRoad };

      AppState.layers.safeZones.clearLayers();
      L.circleMarker([safeLat, safeLon], {
        radius: 10,
        color: '#10B981',
        fillColor: '#059669',
        fillOpacity: 0.95,
        weight: 3
      }).bindPopup(`<b>🛡️ ${safeName}</b><br>Vía de acceso: ${safeRoad}<br>Sector seguro fuera del eje de avance del fuego.`)
        .addTo(AppState.layers.safeZones);

      fetchAndDrawOsrmEscapeRoute(
        AppState.userLocation.lat,
        AppState.userLocation.lon,
        safeLat,
        safeLon,
        safeName,
        safeRoad,
        AppState.routeRequestSeq,
        escapeAzimuth,
        escapeCardinal,
        allEvents
      );
    }

    async function fetchAndDrawOsrmEscapeRoute(uLat, uLon, sLat, sLon, targetName, targetRoad, reqSeq, escapeAzimuth, escapeCardinal, allEvents = []) {
      const uPt = turf.point([uLon, uLat]);
      const sPt = turf.point([sLon, sLat]);
      const bearingToSafe = (turf.bearing(uPt, sPt) + 360) % 360;
      const cardinal = degreesToCardinal(bearingToSafe);

      // Helper para dibujar el Vector Táctico Directo cuando la carretera está cortada por fuego o no hay red
      function drawTacticalFlankVector(reasonLabel) {
        AppState.layers.escapeRoute.clearLayers();

        const tipPt = turf.transformTranslate(uPt, 2.8, escapeAzimuth);
        const wing1Pt = turf.transformTranslate(tipPt, 0.6, (escapeAzimuth + 150) % 360);
        const wing2Pt = turf.transformTranslate(tipPt, 0.6, (escapeAzimuth + 210) % 360);
        const tipLL = [tipPt.geometry.coordinates[1], tipPt.geometry.coordinates[0]];
        const w1LL = [wing1Pt.geometry.coordinates[1], wing1Pt.geometry.coordinates[0]];
        const w2LL = [wing2Pt.geometry.coordinates[1], wing2Pt.geometry.coordinates[0]];

        // Vástago de la flecha verde con halo de advertencia ámbar
        L.polyline([[uLat, uLon], tipLL], {
          color: '#F59E0B',
          weight: 6,
          opacity: 0.85,
          dashArray: '8, 8',
          className: 'animated-escape-path'
        }).addTo(AppState.layers.escapeRoute);

        L.polyline([[uLat, uLon], tipLL], {
          color: '#10B981',
          weight: 3.5,
          opacity: 1.0
        }).addTo(AppState.layers.escapeRoute);

        // Punta triangular
        L.polygon([w1LL, tipLL, w2LL], {
          color: '#065F46',
          fillColor: '#10B981',
          fillOpacity: 1.0,
          weight: 2
        }).addTo(AppState.layers.escapeRoute);

        // Floating Radar Badge sobre la punta de la flecha táctica
        L.marker(tipLL, {
          icon: L.divIcon({
            className: 'escape-floating-badge',
            html: `<span>🧭 HUIR RUMBO ${escapeCardinal} (${Math.round(escapeAzimuth)}°)</span>`,
            iconSize: [210, 24],
            iconAnchor: [105, 12]
          })
        }).addTo(AppState.layers.escapeRoute);

        const popupText = `<b>⚠️ ALERTA: ${reasonLabel}</b><br>` +
          `La vía vial principal atraviesa sectores comprometidos por fuego.<br>` +
          `<b>🧭 VECTOR DE EVACUACIÓN RECOMENDADO:</b><br>` +
          `➜ Desplazarse rumbo <b>${escapeCardinal} (${Math.round(escapeAzimuth)}°)</b> hacia terreno abierto fuera del cono.<br>` +
          `<b>Destino Seguro:</b> ${targetName}`;

        L.popup()
          .setLatLng([(uLat + tipLL[0]) / 2, (uLon + tipLL[1]) / 2])
          .setContent(popupText);

        const desc = document.getElementById('fsm-status-desc');
        if (desc) {
          desc.innerText = `⚠️ ${reasonLabel}. Evacúe a campo abierto rumbo ${escapeCardinal} (${Math.round(escapeAzimuth)}°) para salir del cono.`;
        }

        const statusBadge = document.getElementById('escape-status-badge');
        if (statusBadge) {
          statusBadge.innerText = "⚠️ Vía Cortada";
          statusBadge.className = "text-[9px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse";
        }
        const subtext = document.getElementById('escape-subtext');
        if (subtext) {
          subtext.innerText = "Carretera con fuego: huir a campo abierto";
        }
      }

      try {
        const url = `https://router.project-osrm.org/route/v1/driving/${uLon},${uLat};${sLon},${sLat}?overview=full&geometries=geojson&steps=true`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1800);
        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        if (!res.ok) throw new Error("OSRM HTTP error");
        const data = await res.json();

        // Evita condición de carrera si el usuario salió a Zona Segura antes de responder OSRM
        if (reqSeq !== AppState.routeRequestSeq || !AppState.currentSafeZoneTarget) return;

        if (data.code === "Ok" && data.routes && data.routes.length > 0) {
          const route = data.routes[0];
          const coords = route.geometry.coordinates;

          // VALIDACIÓN TOPOLÓGICA ANTI-CRUCE DE FUEGO (turf.lineIntersect)
          let isRoadCutByFire = false;
          let cutReason = '';
          if (coords && coords.length >= 2) {
            const routeLine = turf.lineString(coords);
            for (const ev of allEvents) {
              if (ev._originalPoly) {
                const cuts = turf.lineIntersect(routeLine, ev._originalPoly);
                if (cuts && cuts.features && cuts.features.length > 0) {
                  isRoadCutByFire = true;
                  cutReason = `Vía cortada por ${ev.event_id}`;
                  break;
                }
              }
              if (ev._cone1h) {
                const cutsCone = turf.lineIntersect(routeLine, ev._cone1h);
                if (cutsCone && cutsCone.features && cutsCone.features.length > 0) {
                  isRoadCutByFire = true;
                  cutReason = `Vía bloqueada por cono de avance 1h (${ev.event_id})`;
                  break;
                }
              }
            }
          }

          // Si la carretera está cortada por el fuego, PROHIBIDO dibujarla
          if (isRoadCutByFire) {
            drawTacticalFlankVector(cutReason);
            return;
          }

          // Si la carretera está libre de fuego, dibujarla en verde normal
          const realDistKm = route.distance / 1000.0;
          const realTimeMin = Math.max(1, Math.round(route.duration / 60.0));
          const latLngs = coords.map(c => [c[1], c[0]]);
          AppState.layers.escapeRoute.clearLayers();

          let roadName = targetRoad || "Red Vial Oficial";
          if (route.legs && route.legs[0] && route.legs[0].steps) {
            const namedStep = route.legs[0].steps.find(s => s.name && s.name.trim().length > 0);
            if (namedStep) roadName = `${namedStep.name} (${targetRoad || ''})`.trim();
          }

          L.polyline(latLngs, {
            color: '#10B981',
            weight: 5,
            opacity: 0.95,
            className: 'animated-escape-path'
          }).bindPopup(`<b>🧭 Ruta Vial Oficial (Despejada)</b><br><b>Destino:</b> ${targetName || 'Zona Segura'}<br><b>Vía:</b> ${roadName}<br><b>Distancia:</b> ${realDistKm.toFixed(1)} km (~${realTimeMin} min)<br><b>Rumbo General:</b> ${cardinal}`)
            .addTo(AppState.layers.escapeRoute);

          const statusBadge = document.getElementById('escape-status-badge');
          if (statusBadge) {
            statusBadge.innerText = "🟢 Vía Libre";
            statusBadge.className = "text-[9px] px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
          }
          const subtext = document.getElementById('escape-subtext');
          if (subtext) {
            subtext.innerText = `Ruta vial oficial (~${realDistKm.toFixed(1)} km, ${realTimeMin} min)`;
          }
          return;
        }
      } catch (e) {
        if (reqSeq !== AppState.routeRequestSeq || !AppState.currentSafeZoneTarget) return;
        drawTacticalFlankVector("Conexión vial no disponible");
      }
    }

    function triggerDemoScenario() {
      switchMainTab('tactical');
      const targetEv = AppState.selectedCluster || (getAllTacticalEvents()[0]);
      if (targetEv) {
        const cPt = turf.point([targetEv.centroid_lon, targetEv.centroid_lat]);
        const polyRadiusKm = getClusterRadiusKm(targetEv);
        // Ubicar al usuario dentro del cono 1h siguiendo el vector de avance del viento demo (205° -> 25°)
        const demoPt = turf.transformTranslate(cPt, Math.min(4.8, polyRadiusKm + 1.0), 25.0);
        AppState.userLocation = {
          lat: demoPt.geometry.coordinates[1],
          lon: demoPt.geometry.coordinates[0]
        };
      } else {
        AppState.userLocation = { lat: -33.2380, lon: -65.9510 };
      }
      AppState.userMarker.setLatLng([AppState.userLocation.lat, AppState.userLocation.lon]);
      map.setView([AppState.userLocation.lat, AppState.userLocation.lon], 13);

      AppState.isUsingInjectedWeather = true;
      AppState.weather.windSpeedKmh = 42.0;
      AppState.weather.windDirectionDeg = 205.0;
      AppState.weather.temperatureC = 35.0;
      AppState.weather.relativeHumidity = 16.0;

      const badge = document.getElementById('hud-telemetry-mode');
      badge.innerText = '🎬 Escenario Demo Crítica Activo';
      badge.className = 'text-[10px] px-2.5 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200 font-bold';

      syncSimulatorSlidersFromWeather();
      updateHudDisplay();
      recalculatePredictiveEngine();
    }

    function openNativeGoogleMaps() {
      const o = `${AppState.userLocation.lat.toFixed(5)},${AppState.userLocation.lon.toFixed(5)}`;
      if (!AppState.currentSafeZoneTarget) {
        window.open(`https://www.google.com/maps/search/?api=1&query=${o}`, '_blank');
        return;
      }
      const d = `${AppState.currentSafeZoneTarget.lat.toFixed(5)},${AppState.currentSafeZoneTarget.lon.toFixed(5)}`;
      window.open(`https://www.google.com/maps/dir/?api=1&origin=${o}&destination=${d}&travelmode=driving`, '_blank');
    }

    function openSosModal() {
      document.getElementById('sos-gps-text').innerText = `${AppState.userLocation.lat.toFixed(5)}, ${AppState.userLocation.lon.toFixed(5)}`;
      document.getElementById('sos-eta-text').innerText = document.getElementById('fsm-eta-display').innerText;
      document.getElementById('sos-wind-text').innerText = `${Math.round(AppState.weather.windSpeedKmh)} km/h`;
      document.getElementById('modal-sos').classList.remove('hidden');
    }

    function closeSosModal() {
      document.getElementById('modal-sos').classList.add('hidden');
    }

    function buildSosMessage() {
      const gps = `${AppState.userLocation.lat.toFixed(5)}, ${AppState.userLocation.lon.toFixed(5)}`;
      const mapsUrl = `https://maps.google.com/?q=${gps}`;
      const eta = document.getElementById('fsm-eta-display').innerText;
      const safeDest = AppState.currentSafeZoneTarget ? AppState.currentSafeZoneTarget.name : 'Zona Segura';
      return `🚨 *SOS EMERGENCIA INCENDIO (SeMF / AURA-FIRE)*\n` +
             `📍 *Ubicación GPS:* ${gps}\n` +
             `🗺️ *Ver en Google Maps:* ${mapsUrl}\n` +
             `⏱️ *Tiempo Estimado Impacto:* ${eta}\n` +
             `🛡️ *Destino de Evacuación:* ${safeDest}\n` +
             `Solicito auxilio urgente de Bomberos y Defensa Civil.`;
    }

    function sendSosWhatsApp() {
      window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(buildSosMessage())}`, '_blank');
      closeSosModal();
    }

    function sendSosSms() {
      window.open(`sms:?body=${encodeURIComponent(buildSosMessage())}`, '_blank');
      closeSosModal();
    }

    function degreesToCardinal(deg) {
      const c = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
      return c[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
    }
  </script>
</body>
</html>
'''

def safe_write_html(target_path: str, content: str):
    data = content.encode("utf-8")
    chunk_size = 1024 * 1024  # 1 MB chunks (evita EINVAL en bind mounts 9P/DrvFs de Docker/WSL2)
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
        except OSError:
            pass
    with open(target_path, "wb") as f:
        for i in range(0, len(data), chunk_size):
            f.write(data[i:i + chunk_size])
        f.flush()


def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    html_content = get_template()

    tactical_path = os.path.join(output_dir, "app_tactica_mobile.html")
    safe_write_html(tactical_path, html_content)

    index_path = os.path.join(output_dir, "index.html")
    safe_write_html(index_path, html_content)

    print(f"📱 Portal Unificado SeMF / AURA-FIRE (2 Pestañas Consolidadas) generado con éxito:")
    print(f"   - {tactical_path} ({os.path.getsize(tactical_path):,} bytes)")
    print(f"   - {index_path} ({os.path.getsize(index_path):,} bytes)")

if __name__ == "__main__":
    main()
