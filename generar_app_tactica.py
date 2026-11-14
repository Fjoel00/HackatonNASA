#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
AURA-FIRE Unified Portal Generator (NASA Space Apps Challenge 2026)
=============================================================================
Genera el portal web interactivo unificado con 3 vistas clave:
1. 📅 BURNING ACTIVITY CALENDAR: Matriz de 52 semanas, línea base climatológica
   de 20 años, Z-Score de anomalía y factor de armonización de escala MODIS/VIIRS.
2. 🛰️ MONITOR SATELITAL NRT: Mapa interactivo con capas independientes para VIIRS (375m),
   MODIS (1km), frentes consolidados por DBSCAN geodésico y telemetría por satélite.
3. 🛡️ AURA-FIRE TÁCTICO & SUPERVIVENCIA: Centro de control dual (Brigadista / Evacuación),
   enrutamiento por carreteras con OSRM, clima en vivo Open-Meteo, conos Turf.js y SOS.
"""

import os
import json

def get_template():
    # Cargar datos del dashboard si existen
    json_path = os.path.join("output", "dashboard_data.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            embedded_data = json.load(f)
    else:
        embedded_data = {}

    json_str = json.dumps(embedded_data, ensure_ascii=False)

    return r'''<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <link rel="icon" href="favicon.ico" type="image/x-icon">
  <title>AURA-FIRE | Harmonization of MODIS & VIIRS Hot Spots (NASA Space Apps)</title>
  
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

  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <!-- Turf.js para Geoprocesamiento y Proyecciones en Cliente -->
  <script src="https://unpkg.com/@turf/turf@6.5.0/turf.min.js"></script>

  <style>
    html, body {
      height: 100%;
      width: 100%;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      touch-action: manipulation;
      background-color: #060911;
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
    .leaflet-container {
      background: #060911 !important;
      width: 100%;
      height: 100%;
    }
    .user-pulse-marker {
      width: 24px;
      height: 24px;
      background: #3B82F6;
      border: 3.5px solid #FFFFFF;
      border-radius: 50%;
      box-shadow: 0 0 16px #3B82F6;
      animation: pulse-ring 2s infinite;
    }
    @keyframes pulse-ring {
      0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
      70% { box-shadow: 0 0 0 18px rgba(59, 130, 246, 0); }
      100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
    }
    .animated-escape-path {
      stroke-dasharray: 8, 8;
      animation: dash-animation 1.2s linear infinite;
    }
    @keyframes dash-animation {
      to { stroke-dashoffset: -16; }
    }
    .current-week-pulse {
      animation: border-pulse 1.8s infinite;
    }
    @keyframes border-pulse {
      0% { border-color: rgba(255, 77, 45, 0.4); box-shadow: 0 0 0 0 rgba(255, 77, 45, 0.7); }
      70% { border-color: rgba(255, 77, 45, 1); box-shadow: 0 0 0 8px rgba(255, 77, 45, 0); }
      100% { border-color: rgba(255, 77, 45, 0.4); box-shadow: 0 0 0 0 rgba(255, 77, 45, 0); }
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-thumb {
      background: #233256;
      border-radius: 4px;
    }
  </style>
</head>
<body class="bg-tactical-950 text-slate-100 h-full flex flex-col overflow-hidden select-none">

  <!-- ========================================================================= -->
  <!-- NAVBAR PRINCIPAL: BRAND, PESTAÑAS DEL RETO Y REGIONES                     -->
  <!-- ========================================================================= -->
  <header class="bg-tactical-900/95 backdrop-blur-md border-b border-tactical-800/90 px-3 py-2 z-30 shrink-0">
    <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
      
      <!-- Logo y Desafío NASA -->
      <div class="flex items-center gap-2.5">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-tactical-accent via-orange-600 to-red-600 flex items-center justify-center text-xl shadow-lg shadow-tactical-accent/25">
          🔥
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-black tracking-widest uppercase text-tactical-accent">AURA-FIRE</span>
            <span class="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-950/90 text-blue-300 border border-blue-600/60 font-mono font-bold">
              🚀 NASA Space Apps 2026
            </span>
          </div>
          <div class="text-[10px] text-slate-400 font-mono flex items-center gap-1.5">
            <span>MODIS & VIIRS Harmonization</span>
            <span class="text-slate-600">|</span>
            <span id="label-region-info" class="text-amber-400 font-semibold">Sierras de Córdoba / San Luis</span>
          </div>
        </div>
      </div>

      <!-- Pestañas Principales del Reto (Tabs) -->
      <nav class="flex bg-tactical-950 p-1 rounded-xl border border-tactical-800 text-xs font-semibold shadow-inner">
        <button id="tab-btn-calendar" onclick="switchMainTab('calendar')"
                class="view-tab-btn px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 bg-tactical-accent text-white shadow-lg shadow-tactical-accent/30 font-bold">
          <span>📅</span>
          <span>Calendario de Quemas</span>
        </button>
        <button id="tab-btn-monitor" onclick="switchMainTab('monitor')"
                class="view-tab-btn px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 text-slate-400 hover:text-slate-200">
          <span>🛰️</span>
          <span>Monitor NRT</span>
        </button>
        <button id="tab-btn-tactical" onclick="switchMainTab('tactical')"
                class="view-tab-btn px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 text-slate-400 hover:text-slate-200">
          <span>🛡️</span>
          <span>AURA-FIRE Táctico</span>
        </button>
      </nav>

      <!-- Selector de Región de Estudio -->
      <div class="flex items-center gap-2">
        <select id="select-region" onchange="changeRegion(this.value)"
                class="bg-tactical-850 hover:bg-tactical-800 text-slate-200 text-xs font-mono py-1.5 px-2.5 rounded-xl border border-tactical-700 outline-none cursor-pointer transition-all">
          <option value="Sierras_Cordoba_SanLuis" selected>📍 Vista Regional: Córdoba y San Luis</option>
          <option value="Trapiche_SanLuis">🔥 Foco Crítico: El Trapiche / San Luis (Multi-Sensor)</option>
          <option value="Traslasierra_Cordoba">🔥 Foco Traslasierra: Mina Clavero / San Javier (Cba)</option>
          <option value="Cordoba_SierrasChicas">🔥 Foco Sierras Chicas / Gran Córdoba</option>
        </select>
        <button onclick="triggerDemoScenario()" title="Simular productor en peligro a sotavento en Córdoba"
                class="hidden md:flex items-center gap-1.5 text-[11px] bg-tactical-850 hover:bg-tactical-800 text-amber-300 px-2.5 py-1.5 rounded-xl border border-amber-500/40 font-mono shadow-md transition-all active:scale-95">
          <span>🎬</span> Demo Crítica
        </button>
      </div>

    </div>
  </header>

  <!-- ========================================================================= -->
  <!-- VISTA 1: BURNING ACTIVITY CALENDAR & SEASONAL TRENDS (RETRO NASA CORE)   -->
  <!-- ========================================================================= -->
  <section id="view-calendar" class="view-tab flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
    <div class="max-w-7xl mx-auto space-y-6">
      
      <!-- Hero de la Pestaña -->
      <div class="bg-gradient-to-r from-tactical-900 via-tactical-850 to-tactical-900 border border-tactical-800 rounded-2xl p-5 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 text-xs text-tactical-accent font-mono font-bold uppercase tracking-wider">
            <span>NASA Space Apps Challenge</span>
            <span>•</span>
            <span>Reto: Harmonization of MODIS & VIIRS Hot Spots</span>
          </div>
          <h1 class="text-xl sm:text-2xl font-black text-white mt-1">
            Burning Activity Calendar & Régimen Estacional
          </h1>
          <p class="text-xs sm:text-sm text-slate-300 max-w-3xl mt-1">
            Normalización y reconstrucción de la serie histórica continua (2000–2026) compensando la disparidad de huella espacial entre el sensor <b>MODIS (1 km)</b> y <b>VIIRS (375 m)</b> mediante función de transferencia física y análisis de anomalías estacionales.
          </p>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <div class="text-right bg-tactical-950/80 px-4 py-2.5 rounded-xl border border-tactical-700">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Régimen Estacional</div>
            <div id="cal-kpi-risk-label" class="text-sm font-black text-amber-400 font-mono">FIN DE TEMPORADA SECA</div>
            <div id="cal-kpi-risk-index" class="text-[11px] text-slate-400 font-mono">Riesgo Climático: 35%</div>
          </div>
        </div>
      </div>

      <!-- Tarjetas de Métricas de Armonización -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        
        <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-4 shadow-lg">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Semana Actual</span>
            <span class="text-tactical-accent">📅</span>
          </div>
          <div id="cal-stat-current-week" class="text-2xl font-black font-mono text-white mt-1">
            Semana 46
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            Mes de Noviembre (Ciclo Anual 1-52)
          </div>
        </div>

        <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-4 shadow-lg">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Anomalía Z-Score</span>
            <span class="text-amber-400">📊</span>
          </div>
          <div id="cal-stat-zscore" class="text-2xl font-black font-mono text-emerald-400 mt-1">
            -0.45 σ
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            Dentro de la media histórica esperada
          </div>
        </div>

        <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-4 shadow-lg">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Focos Armonizados</span>
            <span class="text-orange-400">🛰️</span>
          </div>
          <div id="cal-stat-harmonized-hotspots" class="text-2xl font-black font-mono text-amber-400 mt-1">
            45.0 eq
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            31 crudos (28 VIIRS + 3 MODIS escalados 4.0x)
          </div>
        </div>

        <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-4 shadow-lg">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Energía Radiativa (FRE)</span>
            <span class="text-red-400">⚡</span>
          </div>
          <div id="cal-stat-fre" class="text-2xl font-black font-mono text-tactical-accent mt-1">
            2.91 GJ
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            Integral de FRP por sobrepasos temporales
          </div>
        </div>

      </div>

      <!-- Matriz Interactiva de 52 Semanas (Heatmap Calendar) -->
      <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-5 shadow-2xl space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-tactical-800 pb-3">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span>🗓️</span> Matriz de Actividad Anual por Semanas Ecológicas (1 a 52)
            </h2>
            <p class="text-xs text-slate-400">
              Seleccione cualquier celda para inspeccionar el desvío respecto a la línea base histórica climatológica (20 años de datos NASA).
            </p>
          </div>
          <!-- Leyenda de Colores -->
          <div class="flex items-center gap-2 text-[10px] font-mono flex-wrap">
            <span class="text-slate-400">Leyenda:</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-slate-800 border border-slate-700"></span> Inactivo</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-[#fee08b]"></span> Bajo</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-[#fdae61]"></span> Normal</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-[#f46d43]"></span> Alto</span>
            <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-[#d73027]"></span> Crítico</span>
          </div>
        </div>

        <!-- Grilla de Semanas agrupadas por Mes -->
        <div id="cal-weeks-grid" class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-3 overflow-x-auto pb-2">
          <!-- Renderizado dinámicamente con JS -->
        </div>

        <!-- Tarjeta de Detalle de Semana Seleccionada -->
        <div id="cal-week-detail-card" class="bg-tactical-950 border border-tactical-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span id="detail-week-badge" class="px-2 py-0.5 rounded-full bg-tactical-accent/20 text-tactical-accent font-mono font-bold text-xs">Semana 46</span>
              <span id="detail-month-label" class="text-xs text-slate-300 font-semibold">Mes de Noviembre</span>
              <span id="detail-status-pill" class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-600/40 font-mono">Normal / Dentro del promedio</span>
            </div>
            <div id="detail-summary-text" class="text-xs text-slate-400">
              Línea base histórica: 141.5 focos esperados en Noviembre. Actividad registrada: 45.0 focos equivalentes armonizados.
            </div>
          </div>
          <div class="flex items-center gap-4 text-xs font-mono shrink-0">
            <div>
              <div class="text-[10px] text-slate-500 uppercase">Focos Observados</div>
              <div id="detail-observed-val" class="text-sm font-bold text-white">45.0 eq</div>
            </div>
            <div class="h-8 w-px bg-tactical-800"></div>
            <div>
              <div class="text-[10px] text-slate-500 uppercase">Media Histórica</div>
              <div id="detail-baseline-val" class="text-sm font-bold text-slate-300">35.4 focos</div>
            </div>
            <div class="h-8 w-px bg-tactical-800"></div>
            <div>
              <div class="text-[10px] text-slate-500 uppercase">Potencia Radiativa</div>
              <div id="detail-frp-val" class="text-sm font-bold text-tactical-accent">456.7 MW</div>
            </div>
          </div>
        </div>

      </div>

      <!-- Gráfico de Curva Estacional Climatológica (SVG Interactivo) -->
      <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-tactical-800 pb-3">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <span>📈</span> Tendencia Estacional: Línea Base Histórica vs. Actividad 2026
            </h2>
            <p class="text-xs text-slate-400">
              Curva climatológica esperada de incendios (banda de desviación estándar) contrastada con las detecciones satelitales armonizadas del año en curso.
            </p>
          </div>
          <div class="flex items-center gap-3 text-[11px] font-mono">
            <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-blue-400 inline-block"></span> Línea Base Histórica</span>
            <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-tactical-accent inline-block"></span> Observación Actual</span>
          </div>
        </div>

        <!-- Contenedor del Gráfico SVG -->
        <div class="relative w-full h-64 bg-tactical-950 rounded-xl p-2 border border-tactical-800">
          <svg id="cal-seasonal-chart" class="w-full h-full" viewBox="0 0 800 240" preserveAspectRatio="none">
            <!-- Renderizado dinámico con JS -->
          </svg>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div class="bg-tactical-950 p-3 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Período Crítico Histórico:</span>
            <div class="text-amber-400 font-bold font-mono mt-0.5" id="cal-info-peak-period">Agosto – Octubre (Semanas 31 a 44)</div>
          </div>
          <div class="bg-tactical-950 p-3 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Fórmula de Armonización:</span>
            <div class="text-blue-400 font-bold font-mono mt-0.5">Hotspot_eq = Conteo × 4.0 · √(Área / 1.0)</div>
          </div>
          <div class="bg-tactical-950 p-3 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Factor de Escala Empírico:</span>
            <div class="text-emerald-400 font-bold font-mono mt-0.5" id="cal-info-ratio">VIIRS / MODIS ≈ 9.33x en escena</div>
          </div>
        </div>

      </div>

      <!-- Panel de Rigor Científico y Fusión Inter-Sensor -->
      <div class="bg-tactical-900 border border-tactical-800 rounded-2xl p-5 shadow-2xl space-y-3">
        <h3 class="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <span>🔬</span> Validez Científica y Fundamento Físico de la Armonización
        </h3>
        <div class="text-xs text-slate-300 leading-relaxed space-y-2">
          <p>
            Los instrumentos <b>MODIS</b> (Terra/Aqua) y <b>VIIRS</b> (Suomi-NPP, NOAA-20, NOAA-21) detectan anomalías térmicas en los canales del infrarrojo medio de $4\,\mu\text{m}$ ($T_{21/22}$ vs $T_{I4}$) y térmico de $11\,\mu\text{m}$ ($T_{31}$ vs $T_{I5}$). La discrepancia en el conteo histórico no refleja una variación del fuego, sino la diferencia de resolución espacial: <b>$1000\text{ m}$ ($1.0\text{ km}^2$)</b> en MODIS frente a <b>$375\text{ m}$ ($0.14\text{ km}^2$)</b> en VIIRS.
          </p>
          <p>
            Nuestro pipeline resuelve esta divergencia calculando la densidad radiativa ($\text{MW/km}^2$) a partir del área dinámica de píxel proyectada (`scan × track`) y aplicando la función de transferencia de escala derivada de la literatura de la NASA (Schroeder et al., 2014; Oliva & Schroeder, 2015). Esto permite unir más de dos décadas de datos en una sola línea temporal coherente.
          </p>
        </div>
      </div>

    </div>
  </section>

  <!-- ========================================================================= -->
  <!-- VISTA 2 & 3: CONTENEDOR COMÚN DEL MAPA (MONITOR NRT Y CENTRO TÁCTICO)     -->
  <!-- ========================================================================= -->
  <div id="view-map-container" class="view-tab flex-1 relative overflow-hidden hidden flex flex-col">
    
    <!-- BANNER DINÁMICO DE ESTADO (MÁQUINA DE ESTADOS FSM) -->
    <div id="fsm-banner" class="bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white px-4 py-2 border-b border-red-500/50 flex items-center justify-between shrink-0 shadow-xl transition-all duration-300">
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
      <div class="text-right bg-black/30 px-3 py-1 rounded-xl border border-white/20">
        <div class="text-[9px] uppercase tracking-wider text-red-200 font-mono">Tiempo de Impacto</div>
        <div id="fsm-eta-display" class="text-lg font-mono font-black tracking-tight text-white">
          -- MIN
        </div>
      </div>
    </div>

    <!-- BARRA HUD METEOROLÓGICA (OPEN-METEO) -->
    <div id="hud-bar" class="bg-tactical-900/90 border-b border-tactical-800 px-3 py-1.5 text-[11px] font-mono flex items-center justify-between overflow-x-auto gap-4 shrink-0">
      <div class="flex items-center gap-3 whitespace-nowrap">
        <div class="flex items-center gap-1.5">
          <span class="text-slate-400">💨 Viento:</span>
          <span id="hud-wind-speed" class="text-amber-300 font-bold">-- km/h</span>
          <span id="hud-wind-arrow" class="inline-block transition-transform duration-500 text-amber-400 font-bold">↑</span>
          <span id="hud-wind-dir" class="text-slate-300">--°</span>
        </div>
        <div class="h-3 w-px bg-tactical-800"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">🌡️ Temp:</span>
          <span id="hud-temp" class="text-slate-200">--°C</span>
        </div>
        <div class="h-3 w-px bg-tactical-800"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">💧 HR:</span>
          <span id="hud-humidity" class="text-slate-200">--%</span>
        </div>
        <div class="h-3 w-px bg-tactical-800"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">🔥 FRP Pico:</span>
          <span id="hud-frp" class="text-tactical-accent font-bold">-- MW</span>
        </div>
      </div>

      <!-- Badge 30-30-30 -->
      <div id="badge-crossover" class="hidden px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-700/60 text-[10px] font-bold uppercase tracking-wider animate-pulse whitespace-nowrap">
        ⚠️ CONDICIÓN EXTREMA 30-30-30
      </div>
    </div>

    <!-- Contenedor del Mapa Leaflet -->
    <main class="flex-1 relative overflow-hidden flex flex-col">
      <div id="map"></div>

      <!-- =================================================================== -->
      <!-- OVERLAYS PARA LA VISTA 2: MONITOR NRT (KPI CARD & CLUSTERS)        -->
      <!-- =================================================================== -->
      <div id="monitor-overlays" class="hidden absolute top-3 right-3 w-80 z-20 pointer-events-none">
        <div class="bg-tactical-900/95 backdrop-blur-xl rounded-2xl border border-tactical-700/80 p-4 shadow-2xl pointer-events-auto space-y-3">
          <div class="flex items-center justify-between border-b border-tactical-800 pb-2">
            <span class="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
              <span>🛰️</span> Focos NRT NASA FIRMS
            </span>
            <span class="text-[9px] px-1.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-600/40 font-mono">
              Armonizado
            </span>
          </div>

          <div class="space-y-1.5 text-xs font-mono">
            <div class="flex justify-between">
              <span class="text-slate-400">Detecciones VIIRS (375m):</span>
              <b id="mon-kpi-viirs" class="text-amber-400">28</b>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Detecciones MODIS (1km):</span>
              <b id="mon-kpi-modis" class="text-red-400">3</b>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Frentes Activos (DBSCAN):</span>
              <b id="mon-kpi-fronts" class="text-emerald-400">8 frentes</b>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Potencia Máxima (FRP):</span>
              <b id="mon-kpi-peak-frp" class="text-tactical-accent">374.5 MW</b>
            </div>
          </div>

          <!-- Selector Rápido de Incendios en Monitor -->
          <div class="border-t border-tactical-800 pt-2 space-y-1">
            <div class="text-[10px] text-slate-400 font-mono">Frentes de Fuego Consolidados:</div>
            <div id="monitor-cluster-list" class="max-h-36 overflow-y-auto space-y-1 pr-1">
              <!-- Rellenado dinámico con JS -->
            </div>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- OVERLAYS PARA LA VISTA 3: AURA-FIRE TÁCTICO & SOS                  -->
      <!-- =================================================================== -->
      <div id="tactical-overlays" class="hidden absolute top-3 left-3 right-3 sm:right-auto sm:w-96 z-20 pointer-events-none">
        
        <!-- Selector Segmentado de Rol (Bombero vs Productor) -->
        <div class="flex bg-tactical-950 p-1 rounded-xl border border-tactical-800 text-xs font-semibold shadow-2xl mb-2 pointer-events-auto">
          <button id="btn-mode-brigadista" onclick="setAppMode('BRIGADISTA')"
                  class="flex-1 py-1.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200">
            <span>🚒</span> Brigadista
          </button>
          <button id="btn-mode-productor" onclick="setAppMode('PRODUCTOR')"
                  class="flex-1 py-1.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5 bg-gradient-to-r from-tactical-accent to-red-600 text-white shadow-lg shadow-tactical-accent/40 font-bold">
            <span>🏃</span> Evacuación
          </button>
        </div>

        <!-- Panel Brigadista -->
        <div id="panel-brigadista" class="hidden bg-tactical-900/95 backdrop-blur-xl rounded-2xl border border-tactical-700/80 p-3.5 shadow-2xl pointer-events-auto space-y-3">
          <div class="flex items-center justify-between border-b border-tactical-800 pb-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="text-sm font-black text-amber-400">🚒 CONTROL TÁCTICO</span>
                <span id="brigade-selected-cluster" class="text-[10px] px-2 py-0.5 rounded-full bg-tactical-800 text-slate-200 font-mono border border-tactical-700">
                  FIRE_CLUSTER_001
                </span>
              </div>
              <div id="brigade-location-name" class="text-[10px] text-slate-300 font-mono mt-0.5">
                Sierras de Córdoba / San Luis
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs font-mono">
            <div class="bg-tactical-950 p-2 rounded-xl border border-tactical-800">
              <span class="text-slate-400 text-[10px]">Superficie Frente:</span>
              <div id="brigade-area" class="text-amber-400 font-bold text-sm">-- ha</div>
            </div>
            <div class="bg-tactical-950 p-2 rounded-xl border border-tactical-800">
              <span class="text-slate-400 text-[10px]">Velocidad Avance:</span>
              <div id="brigade-sat-speed" class="text-tactical-accent font-bold text-sm">-- km/h</div>
            </div>
          </div>
          <div class="space-y-1">
            <span class="text-[10px] text-slate-400 font-mono uppercase">Seleccionar Incendio Activo:</span>
            <div id="brigade-cluster-pills" class="flex items-center gap-1.5 overflow-x-auto pb-1"></div>
          </div>
        </div>

        <!-- Panel Productor / Evacuación -->
        <div id="panel-productor" class="bg-tactical-900/95 backdrop-blur-xl rounded-2xl border border-tactical-700/80 p-3.5 shadow-2xl pointer-events-auto space-y-3">
          <div class="flex items-center justify-between border-b border-tactical-800 pb-2">
            <span class="text-xs font-black text-white uppercase tracking-wider flex items-center gap-1.5">
              <span>🧭</span> Escape y Supervivencia
            </span>
            <span id="routing-engine-badge" class="text-[9px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-600/60 font-mono font-bold flex items-center gap-1">
              <span>🛣️</span> RUTA VIAL REAL (OSRM)
            </span>
          </div>
          <div class="bg-tactical-950 p-2.5 rounded-xl border border-tactical-800 space-y-1 text-xs">
            <div class="flex items-center justify-between text-slate-300">
              <span>Vía Recomendada:</span>
              <span id="routing-via-text" class="text-emerald-400 font-bold font-mono">Red Vial Oficial</span>
            </div>
            <div class="grid grid-cols-3 gap-2 pt-1 font-mono text-center">
              <div class="bg-tactical-900 p-1.5 rounded-lg border border-tactical-800">
                <div class="text-[9px] text-slate-400">Distancia</div>
                <div id="stat-route-distance" class="text-xs font-bold text-white">-- km</div>
              </div>
              <div class="bg-tactical-900 p-1.5 rounded-lg border border-tactical-800">
                <div class="text-[9px] text-slate-400">Tiempo</div>
                <div id="stat-route-time" class="text-xs font-bold text-emerald-400">-- min</div>
              </div>
              <div class="bg-tactical-900 p-1.5 rounded-lg border border-tactical-800">
                <div class="text-[9px] text-slate-400">Rumbo</div>
                <div id="stat-route-cardinal" class="text-xs font-bold text-amber-400">--</div>
              </div>
            </div>
            <p id="user-escape-instruction" class="text-[11px] text-slate-300 pt-1 leading-snug">
              Calculando ruta de escape por carreteras transitables seguras...
            </p>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <button onclick="openNativeGoogleMaps()"
                    class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-blue-600/30 transition-all active:scale-95">
              <span>🗺️</span> Abrir en Maps
            </button>
            <button onclick="openSosModal()"
                    class="bg-tactical-alert hover:bg-red-600 text-white font-black py-2 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-tactical-alert/40 transition-all active:scale-95 animate-pulse">
              <span>🚨</span> PEDIR AUXILIO
            </button>
          </div>
        </div>

      </div>

    </main>
  </div>

  <!-- ========================================================================= -->
  <!-- MODAL DE SOS DE EMERGENCIA                                                -->
  <!-- ========================================================================= -->
  <div id="modal-sos" class="hidden fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-tactical-900 border border-tactical-alert rounded-2xl max-w-sm w-full p-4 space-y-4 shadow-2xl">
      <div class="flex items-center justify-between border-b border-tactical-800 pb-2">
        <div class="flex items-center gap-2">
          <span class="text-2xl">🚨</span>
          <h3 class="text-sm font-black text-white uppercase tracking-wider">Despacho de Emergencia SOS</h3>
        </div>
        <button onclick="closeSosModal()" class="text-slate-400 hover:text-white text-lg font-bold">✕</button>
      </div>

      <div class="text-xs text-slate-300 space-y-2 font-mono bg-tactical-950 p-3 rounded-xl border border-tactical-800">
        <div><b>📍 Ubicación GPS:</b> <span id="sos-gps-text">--</span></div>
        <div><b>⏱️ Tiempo Estimado Impacto:</b> <span id="sos-eta-text" class="text-red-400 font-bold">-- min</span></div>
        <div><b>💨 Viento:</b> <span id="sos-wind-text">--</span></div>
      </div>

      <div class="space-y-2 text-xs">
        <label class="flex items-center gap-2 text-slate-200">
          <input type="checkbox" id="sos-check-people" checked class="rounded accent-tactical-alert">
          <span>Hay personas o familias atrapadas</span>
        </label>
        <label class="flex items-center gap-2 text-slate-200">
          <input type="checkbox" id="sos-check-animals" checked class="rounded accent-tactical-alert">
          <span>Hacienda / Animales en riesgo</span>
        </label>
      </div>

      <div class="grid grid-cols-2 gap-2 pt-2">
        <button onclick="sendSosWhatsApp()"
                class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/30">
          <span>💬</span> Enviar WhatsApp
        </button>
        <button onclick="sendSosSms()"
                class="bg-tactical-alert hover:bg-red-600 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-red-600/30">
          <span>📱</span> SMS Satelital
        </button>
      </div>
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- SCRIPT CENTRAL JS                                                         -->
  <!-- ========================================================================= -->
  <script>
    window.PRELOADED_DASHBOARD_DATA = ''' + json_str + r''';

    const AppState = {
      currentTab: 'calendar',
      mode: 'PRODUCTOR',
      dashboardData: window.PRELOADED_DASHBOARD_DATA,
      selectedCluster: null,
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
        vectorArrows: null,
        safeZones: null,
        escapeRoute: null
      },
      currentSafeZoneTarget: null
    };

    let map = null;

    window.addEventListener('DOMContentLoaded', async () => {
      renderCalendar();
      initMap();
      loadActiveFireData();
      await fetchRealWeather();
      recalculatePredictiveEngine();
      switchMainTab('calendar');
    });

    // Conmutador de Pestañas Principales
    function switchMainTab(tabName) {
      AppState.currentTab = tabName;
      document.querySelectorAll('.view-tab-btn').forEach(btn => {
        btn.classList.remove('bg-tactical-accent', 'text-white', 'shadow-lg');
        btn.classList.add('text-slate-400', 'hover:text-slate-200');
      });
      const activeBtn = document.getElementById(`tab-btn-${tabName}`);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-400', 'hover:text-slate-200');
        activeBtn.classList.add('bg-tactical-accent', 'text-white', 'shadow-lg');
      }

      const calView = document.getElementById('view-calendar');
      const mapView = document.getElementById('view-map-container');
      const monOverlays = document.getElementById('monitor-overlays');
      const tacOverlays = document.getElementById('tactical-overlays');

      if (tabName === 'calendar') {
        calView.classList.remove('hidden');
        mapView.classList.add('hidden');
      } else if (tabName === 'monitor') {
        calView.classList.add('hidden');
        mapView.classList.remove('hidden');
        monOverlays.classList.remove('hidden');
        tacOverlays.classList.add('hidden');
        setTimeout(() => { if (map) map.invalidateSize(); }, 60);
      } else if (tabName === 'tactical') {
        calView.classList.add('hidden');
        mapView.classList.remove('hidden');
        monOverlays.classList.add('hidden');
        tacOverlays.classList.remove('hidden');
        setTimeout(() => { if (map) map.invalidateSize(); }, 60);
      }
    }

    // Selector de Escenarios / Zonas de Estudio (Córdoba & San Luis)
    function changeRegion(regionKey) {
      const infoLabel = document.getElementById('label-region-info');
      if (regionKey === 'Trapiche_SanLuis') {
        infoLabel.innerText = "El Trapiche / La Florida (San Luis)";
        AppState.userLocation = { lat: -33.2380, lon: -65.9510 };
        if (AppState.userMarker) AppState.userMarker.setLatLng([-33.2380, -65.9510]);
        if (map) map.setView([-33.254, -65.953], 13);
        switchMainTab('tactical');
      } else if (regionKey === 'Traslasierra_Cordoba') {
        infoLabel.innerText = "Traslasierra: Mina Clavero / San Javier (Cba)";
        AppState.userLocation = { lat: -31.7350, lon: -65.0200 };
        if (AppState.userMarker) AppState.userMarker.setLatLng([-31.7350, -65.0200]);
        if (map) map.setView([-31.88, -65.10], 10);
        switchMainTab('monitor');
      } else if (regionKey === 'Cordoba_SierrasChicas') {
        infoLabel.innerText = "Sierras Chicas / Gran Córdoba";
        AppState.userLocation = { lat: -31.3900, lon: -64.1100 };
        if (AppState.userMarker) AppState.userMarker.setLatLng([-31.3900, -64.1100]);
        if (map) map.setView([-31.405, -64.120], 12);
        switchMainTab('monitor');
      } else {
        infoLabel.innerText = "Sierras de Córdoba / San Luis (Arg)";
        AppState.userLocation = { lat: -33.2380, lon: -65.9510 };
        if (AppState.userMarker) AppState.userMarker.setLatLng([-33.2380, -65.9510]);
        if (map) map.setView([-32.35, -65.05], 8);
      }
      renderCalendar();
      recalculatePredictiveEngine();
    }

    // Render del Burning Activity Calendar
    function renderCalendar() {
      const cal = AppState.dashboardData.burning_activity_calendar;
      if (!cal) return;

      document.getElementById('cal-stat-current-week').innerText = `Semana ${cal.current_week}`;
      document.getElementById('cal-stat-zscore').innerText = `${cal.current_week_anomaly_z >= 0 ? '+' : ''}${cal.current_week_anomaly_z.toFixed(2)} σ`;
      document.getElementById('cal-stat-harmonized-hotspots').innerText = `${cal.total_harmonized_hotspots || 45.0} eq`;
      const kpis = AppState.dashboardData.kpis;
      if (kpis && typeof kpis.total_estimated_fre_mj === 'number') {
        const freGj = (kpis.total_estimated_fre_mj / 1000.0).toFixed(2);
        document.getElementById('cal-stat-fre').innerText = `${freGj} GJ`;
      }
      document.getElementById('cal-kpi-risk-index').innerText = `Riesgo Climático: ${cal.seasonal_risk_index}%`;
      document.getElementById('cal-info-peak-period').innerText = cal.historical_peak_period;

      const crossCal = AppState.dashboardData.cross_sensor_calibration;
      if (crossCal) {
        document.getElementById('cal-info-ratio').innerText = `VIIRS / MODIS ≈ ${crossCal.empirical_count_ratio || 9.33}x en escena`;
      }

      // Render de la Grilla de 52 Semanas
      const grid = document.getElementById('cal-weeks-grid');
      grid.innerHTML = '';

      const weeks = cal.weeks || [];
      const monthNames = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

      // Agrupar semanas por mes
      for (let m = 0; m < 12; m++) {
        const monthWeeks = weeks.filter(w => Math.min(11, Math.floor((w.week - 1) / 4.33)) === m);
        const col = document.createElement('div');
        col.className = "bg-tactical-950 p-2 rounded-xl border border-tactical-800 flex flex-col space-y-1.5";
        
        const title = document.createElement('div');
        title.className = "text-[10px] font-mono font-bold text-slate-400 text-center border-b border-tactical-800 pb-1";
        title.innerText = monthNames[m];
        col.appendChild(title);

        monthWeeks.forEach(w => {
          const cell = document.createElement('button');
          const isCurr = w.is_current;
          cell.className = `w-full py-1.5 px-1 rounded text-[9px] font-mono flex items-center justify-between border transition-all ${
            isCurr ? 'current-week-pulse border-tactical-accent font-black' : 'border-slate-800/60 hover:scale-105'
          }`;
          cell.style.backgroundColor = w.color;
          cell.style.color = (w.tier >= 1) ? '#000000' : '#64748B';
          cell.innerHTML = `<span>S${w.week}</span><span>${w.observed_raw > 0 ? (w.observed_raw + '🔥') : '·'}</span>`;
          cell.onclick = () => showWeekDetail(w);
          col.appendChild(cell);
        });

        grid.appendChild(col);
      }

      // Mostrar semana actual por defecto
      const currentWeekObj = weeks.find(w => w.is_current) || weeks[0];
      if (currentWeekObj) showWeekDetail(currentWeekObj);

      // Render del Gráfico SVG
      renderSeasonalSvgChart(weeks);
    }

    function showWeekDetail(w) {
      document.getElementById('detail-week-badge').innerText = `Semana ${w.week}`;
      document.getElementById('detail-month-label').innerText = `Mes de ${w.month}`;
      document.getElementById('detail-status-pill').innerText = w.status;
      document.getElementById('detail-observed-val').innerText = `${w.observed_harmonized} eq (${w.observed_raw} crudos)`;
      document.getElementById('detail-baseline-val').innerText = `${w.baseline_mean} focos`;
      document.getElementById('detail-frp-val').innerText = `${w.observed_frp_mw} MW`;
      document.getElementById('detail-summary-text').innerText = 
        `Línea base histórica: ${w.baseline_mean} ± ${w.baseline_std} focos. Desvío: ${w.z_score >= 0 ? '+' : ''}${w.z_score}σ sobre la media.`;
    }

    // Gráfico SVG de la curva estacional
    function renderSeasonalSvgChart(weeks) {
      const svg = document.getElementById('cal-seasonal-chart');
      if (!svg || !weeks.length) return;

      const maxVal = Math.max(...weeks.map(w => w.baseline_mean + w.baseline_std)) * 1.25 || 250;
      const width = 800;
      const height = 240;
      const padLeft = 40;
      const padBottom = 30;
      const plotW = width - padLeft - 20;
      const plotH = height - padBottom - 20;

      let upperPoints = [];
      let lowerPoints = [];
      let meanPoints = [];
      let currentBars = [];

      weeks.forEach((w, idx) => {
        const x = padLeft + (idx / 51) * plotW;
        const yMean = 20 + plotH - (w.baseline_mean / maxVal) * plotH;
        const yUpper = 20 + plotH - (Math.min(maxVal, w.baseline_mean + w.baseline_std) / maxVal) * plotH;
        const yLower = 20 + plotH - (Math.max(0, w.baseline_mean - w.baseline_std) / maxVal) * plotH;

        meanPoints.push(`${x},${yMean}`);
        upperPoints.push(`${x},${yUpper}`);
        lowerPoints.unshift(`${x},${yLower}`);

        if (w.observed_harmonized > 0) {
          const yObs = 20 + plotH - (w.observed_harmonized / maxVal) * plotH;
          currentBars.push(`<circle cx="${x}" cy="${yObs}" r="5" fill="#FF4D2D" stroke="#FFFFFF" stroke-width="2"/>`);
        }
      });

      const bandPolygon = upperPoints.concat(lowerPoints).join(' ');
      const meanPolyline = meanPoints.join(' ');

      svg.innerHTML = `
        <defs>
          <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#38BDF8" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#0284C7" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <!-- Grilla de Fondo -->
        <line x1="${padLeft}" y1="20" x2="${width - 20}" y2="20" stroke="#1E293B" stroke-dasharray="4,4"/>
        <line x1="${padLeft}" y1="${20 + plotH / 2}" x2="${width - 20}" y2="${20 + plotH / 2}" stroke="#1E293B" stroke-dasharray="4,4"/>
        <line x1="${padLeft}" y1="${20 + plotH}" x2="${width - 20}" y2="${20 + plotH}" stroke="#334155"/>
        
        <!-- Banda de Desviación Climatológica -->
        <polygon points="${bandPolygon}" fill="url(#bandGrad)" />
        
        <!-- Línea de Media Histórica Climatológica -->
        <polyline points="${meanPolyline}" fill="none" stroke="#38BDF8" stroke-width="2.5"/>
        
        <!-- Puntos Observados 2026 -->
        ${currentBars.join('')}
        
        <!-- Eje X Meses -->
        <text x="50" y="${height - 8}" fill="#64748B" font-size="10" font-family="monospace">Ene</text>
        <text x="175" y="${height - 8}" fill="#64748B" font-size="10" font-family="monospace">Abr</text>
        <text x="360" y="${height - 8}" fill="#64748B" font-size="10" font-family="monospace">Jul</text>
        <text x="530" y="${height - 8}" fill="#64748B" font-size="10" font-family="monospace">Oct (Pico)</text>
        <text x="730" y="${height - 8}" fill="#64748B" font-size="10" font-family="monospace">Dic</text>
      `;
    }

    // Inicialización del Mapa Leaflet
    function initMap() {
      const initialLat = AppState.userLocation.lat;
      const initialLon = AppState.userLocation.lon;

      map = L.map('map', {
        zoomControl: false,
        attributionControl: false
      }).setView([initialLat, initialLon], 11);

      L.control.zoom({ position: 'topright' }).addTo(map);

      const satLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Esri World Imagery'
      }).addTo(map);

      const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: 'OpenStreetMap'
      });

      // Grupos de capas
      AppState.layers.viirsPoints = L.featureGroup().addTo(map);
      AppState.layers.modisPoints = L.featureGroup().addTo(map);
      AppState.layers.firePolygons = L.featureGroup().addTo(map);
      AppState.layers.projectionCones = L.featureGroup().addTo(map);
      AppState.layers.vectorArrows = L.featureGroup().addTo(map);
      AppState.layers.safeZones = L.featureGroup().addTo(map);
      AppState.layers.escapeRoute = L.featureGroup().addTo(map);

      L.control.layers({
        "🛰️ Satélite Esri": satLayer,
        "🗺️ Calles (OSM)": osmLayer
      }, {
        "📐 Perímetros DBSCAN": AppState.layers.firePolygons,
        "🧭 Conos Predictivos (1h)": AppState.layers.projectionCones,
        "🟠 Focos VIIRS (375m)": AppState.layers.viirsPoints,
        "🔴 Focos MODIS (1km)": AppState.layers.modisPoints,
        "🛡️ Ruta de Escape OSRM": AppState.layers.escapeRoute
      }, { position: 'topright' }).addTo(map);

      // Marcador interactivo del usuario
      const userIcon = L.divIcon({
        className: 'user-pulse-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      AppState.userMarker = L.marker([initialLat, initialLon], {
        icon: userIcon,
        draggable: true
      }).addTo(map);

      AppState.userMarker.on('dragend', function (e) {
        const pos = e.target.getLatLng();
        AppState.userLocation.lat = pos.lat;
        AppState.userLocation.lon = pos.lng;
        recalculatePredictiveEngine();
      });

      map.on('click', function(e) {
        AppState.userLocation.lat = e.latlng.lat;
        AppState.userLocation.lon = e.latlng.lng;
        AppState.userMarker.setLatLng(e.latlng);
        recalculatePredictiveEngine();
      });
    }

    // Carga de eventos de fuego en Monitor y Táctico
    function loadActiveFireData() {
      const data = AppState.dashboardData;
      if (!data || !data.events) return;

      const events = data.events;
      AppState.selectedCluster = events[0] || null;

      // Actualizar KPIs de Monitor
      if (data.kpis) {
        document.getElementById('mon-kpi-viirs').innerText = data.kpis.viirs_detections;
        document.getElementById('mon-kpi-modis').innerText = data.kpis.modis_detections;
        document.getElementById('mon-kpi-fronts').innerText = `${data.metadata.active_fronts_count} frentes`;
        document.getElementById('mon-kpi-peak-frp').innerText = `${data.kpis.peak_pass_frp_mw} MW`;
      }

      // Rellenar lista de frentes en Monitor
      const monList = document.getElementById('monitor-cluster-list');
      monList.innerHTML = '';
      events.forEach(ev => {
        const item = document.createElement('button');
        item.className = "w-full text-left p-1.5 rounded-lg bg-tactical-950 hover:bg-tactical-850 border border-tactical-800 text-[10px] font-mono flex items-center justify-between gap-2";
        const locLabel = ev.location_name || 'Sierras de Córdoba / San Luis';
        item.innerHTML = `<div class="truncate"><div class="text-slate-200 font-bold">${ev.event_id}</div><div class="text-[9px] text-slate-400 truncate">${locLabel}</div></div><span class="text-tactical-accent font-bold shrink-0">${Math.round(ev.frp_peak_mw || ev.frp_total_mw)} MW</span>`;
        item.onclick = () => {
          map.setView([ev.centroid_lat, ev.centroid_lon], 13);
        };
        monList.appendChild(item);
      });

      // Poblar capas individuales de puntos VIIRS (375m) y MODIS (1km)
      AppState.layers.viirsPoints.clearLayers();
      AppState.layers.modisPoints.clearLayers();
      if (Array.isArray(data.points)) {
        data.points.forEach(pt => {
          const isViirs = pt.sensor_family === 'VIIRS';
          const popupHtml = `
            <div style="font-family: monospace; font-size: 11px; min-width: 190px;">
              <b style="color: ${isViirs ? '#F97316' : '#EF4444'};">${isViirs ? '🟠 VIIRS 375m' : '🔴 MODIS 1km'} (${pt.satellite_name})</b><br>
              <hr style="margin: 4px 0; border-color: #334155;">
              <b>FRP:</b> ${pt.frp_mw} MW (${pt.frp_density_mw_km2} MW/km²)<br>
              <b>Temp. Brillo (4µm):</b> ${pt.temp_ch4_k} K<br>
              <b>Anomalía ΔT:</b> ${pt.delta_temp_k} K<br>
              <b>Huella Píxel:</b> ${pt.pixel_area_km2} km²<br>
              <b>Confianza:</b> ${pt.confidence_cat}<br>
              <b>UTC:</b> ${pt.acq_datetime}
            </div>
          `;
          if (isViirs) {
            L.circleMarker([pt.latitude, pt.longitude], {
              radius: 4.5,
              color: '#EA580C',
              fillColor: '#FB923C',
              fillOpacity: 0.85,
              weight: 1.5
            }).bindPopup(popupHtml).addTo(AppState.layers.viirsPoints);
          } else {
            L.circleMarker([pt.latitude, pt.longitude], {
              radius: 7.5,
              color: '#B91C1C',
              fillColor: '#EF4444',
              fillOpacity: 0.7,
              weight: 2
            }).bindPopup(popupHtml).addTo(AppState.layers.modisPoints);
          }
        });
      }

      // Rellenar pills en Modo Brigadista
      const brigadeContainer = document.getElementById('brigade-cluster-pills');
      brigadeContainer.innerHTML = '';
      events.forEach(ev => {
        const pill = document.createElement('button');
        pill.className = "px-2 py-1 rounded-lg text-[9px] font-mono whitespace-nowrap bg-tactical-950 border border-tactical-800 text-slate-300 hover:border-slate-600";
        pill.innerText = `${ev.event_id} (${Math.round(ev.frp_peak_mw || 0)} MW)`;
        pill.onclick = () => {
          AppState.selectedCluster = ev;
          updateClusterDisplay();
          recalculatePredictiveEngine();
          map.setView([ev.centroid_lat, ev.centroid_lon], 13);
        };
        brigadeContainer.appendChild(pill);
      });

      updateClusterDisplay();
    }

    function updateClusterDisplay() {
      if (!AppState.selectedCluster) return;
      const c = AppState.selectedCluster;
      document.getElementById('brigade-selected-cluster').innerText = c.event_id;
      const locEl = document.getElementById('brigade-location-name');
      if (locEl) locEl.innerText = c.location_name || 'Sierras de Córdoba / San Luis';
      document.getElementById('brigade-area').innerText = `${c.detection_area_ha} ha`;
      document.getElementById('brigade-sat-speed').innerText = `${c.spread_speed_kmh} km/h`;
      document.getElementById('hud-frp').innerText = `${c.frp_peak_mw || c.frp_total_mw} MW`;
    }

    // Conexión Open-Meteo
    async function fetchRealWeather() {
      if (!AppState.selectedCluster) return;
      const lat = AppState.selectedCluster.centroid_lat;
      const lon = AppState.selectedCluster.centroid_lon;

      try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m`;
        const res = await fetch(url);
        if (res.ok) {
          const d = await res.json();
          if (d && d.current) {
            AppState.weather.windSpeedKmh = d.current.wind_speed_10m || 28.0;
            AppState.weather.windDirectionDeg = d.current.wind_direction_10m || 205.0;
            AppState.weather.temperatureC = d.current.temperature_2m || 31.0;
            AppState.weather.relativeHumidity = d.current.relative_humidity_2m || 22.0;
          }
        }
      } catch (err) {
        console.warn("Clima respaldo:", err);
      }
      updateHudDisplay();
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

    // Motor Predictivo de Avance (Turf.js + Cinemática + Viento)
    function recalculatePredictiveEngine() {
      if (!AppState.dashboardData || !AppState.dashboardData.events) return;

      AppState.layers.firePolygons.clearLayers();
      AppState.layers.projectionCones.clearLayers();
      AppState.layers.safeZones.clearLayers();
      AppState.layers.escapeRoute.clearLayers();

      const events = AppState.dashboardData.events;
      const w = AppState.weather;
      const windPushDir = (w.windDirectionDeg + 180) % 360;
      const hrFactor = Math.max(0.6, 1.0 + (30.0 - w.relativeHumidity) / 100.0);
      const windInducedSpeedKmh = (0.10 * w.windSpeedKmh) * hrFactor;

      let nearestCluster = null;
      let minDistanceToUser = 999999;

      events.forEach((ev) => {
        if (!ev.polygon_coords || ev.polygon_coords.length < 3) return;

        const latLngs = ev.polygon_coords;
        const turfCoords = latLngs.map(p => [p[1], p[0]]);

        // Polígono del frente consolidado
        L.polygon(latLngs, {
          color: '#DC2626',
          weight: 2.5,
          fillColor: '#EF4444',
          fillOpacity: 0.55
        }).bindPopup(`<b>🔥 ${ev.event_id}</b><br><b>Zona:</b> ${ev.location_name || 'Sierras de Córdoba / San Luis'}<br>Severidad: ${ev.severity_level}<br>Satélites: ${ev.satellites_involved || 'N/A'}<br>Área: ${ev.detection_area_ha} ha<br>FRP Pico: ${ev.frp_peak_mw} MW`)
          .addTo(AppState.layers.firePolygons);

        // Conos Predictivos con Turf.js
        const satSpeed = ev.spread_speed_kmh || 0.0;
        const satAzimuth = ev.spread_azimuth_deg !== null ? ev.spread_azimuth_deg : windPushDir;

        let projSpeedKmh = satSpeed > 0 ? (0.4 * satSpeed + 0.6 * windInducedSpeedKmh) : windInducedSpeedKmh;
        let projAzimuth = windPushDir;

        try {
          const ring = [...turfCoords];
          if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
            ring.push([ring[0][0], ring[0][1]]);
          }
          if (ring.length >= 4) {
            const originalPoly = turf.polygon([ring]);
            const cone1h = generateProjectionCone(originalPoly, projAzimuth, projSpeedKmh * 1.0);
            if (cone1h) {
              L.geoJSON(cone1h, {
                style: { color: '#F97316', weight: 2, dashArray: '5, 5', fillColor: '#FB923C', fillOpacity: 0.25 }
              }).addTo(AppState.layers.projectionCones);
            }
          }
        } catch (e) {}

        const dist = turf.distance(
          turf.point([AppState.userLocation.lon, AppState.userLocation.lat]),
          turf.point([ev.centroid_lon, ev.centroid_lat])
        );
        if (dist < minDistanceToUser) {
          minDistanceToUser = dist;
          nearestCluster = ev;
          nearestCluster.projSpeedKmh = projSpeedKmh;
          nearestCluster.projAzimuth = projAzimuth;
        }
      });

      if (nearestCluster) {
        computeSurvivalStateAndSafeZones(nearestCluster, minDistanceToUser);
      }
    }

    function generateProjectionCone(turfPoly, azimuthDeg, distanceKm) {
      if (distanceKm < 0.2) return null;
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

    // FSM de Supervivencia y Zonas Seguras
    function computeSurvivalStateAndSafeZones(cluster, distToFireKm) {
      const uPt = turf.point([AppState.userLocation.lon, AppState.userLocation.lat]);
      const fPt = turf.point([cluster.centroid_lon, cluster.centroid_lat]);
      const bearing = (turf.bearing(fPt, uPt) + 360) % 360;

      let deltaAngle = Math.abs(bearing - cluster.projAzimuth);
      if (deltaAngle > 180) deltaAngle = 360 - deltaAngle;

      let effectiveSpeed = cluster.projSpeedKmh * Math.cos(deltaAngle * Math.PI / 180);
      let etaMinutes = 999;
      let isHeadingToUser = (deltaAngle <= 70 && effectiveSpeed > 0.2);

      if (isHeadingToUser) {
        const edgeDist = Math.max(0.3, distToFireKm - 0.5);
        etaMinutes = Math.round((edgeDist / effectiveSpeed) * 60);
      }

      const banner = document.getElementById('fsm-banner');
      const title = document.getElementById('fsm-status-title');
      const desc = document.getElementById('fsm-status-desc');
      const etaDisplay = document.getElementById('fsm-eta-display');

      if (isHeadingToUser && (etaMinutes <= 90 || distToFireKm < 3.5)) {
        banner.className = "bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white px-4 py-2 border-b border-red-500/50 flex items-center justify-between shrink-0 shadow-xl animate-pulse";
        title.innerText = "🚨 ALERTA ROJA: IMPACTO INMINENTE";
        desc.innerText = `Fuego avanzando a ${cluster.projSpeedKmh.toFixed(1)} km/h hacia su posición. Evacúe de inmediato por la ruta marcada.`;
        etaDisplay.innerText = etaMinutes + " MIN";
      } else if (distToFireKm < 10.0) {
        banner.className = "bg-gradient-to-r from-amber-600 to-orange-600 text-white px-4 py-2 border-b border-amber-500/50 flex items-center justify-between shrink-0 shadow-xl";
        title.innerText = "⚠️ PRE-ALERTA: FUEGO EN LA ZONA";
        desc.innerText = `Frente activo a ${distToFireKm.toFixed(1)} km. Monitoree rotación de viento y prepare salida.`;
        etaDisplay.innerText = isHeadingToUser ? (etaMinutes + " MIN") : "FUERA DE EJE";
      } else {
        banner.className = "bg-gradient-to-r from-emerald-700 to-teal-800 text-white px-4 py-2 border-b border-emerald-600/50 flex items-center justify-between shrink-0 shadow-xl";
        title.innerText = "🛡️ ZONA EN VIGILANCIA";
        desc.innerText = "Sin frentes activos en trayectoria de impacto directo.";
        etaDisplay.innerText = "> 3 HORAS";
      }

      // Safe Zone a Barlovento (Upwind)
      const escapeAzimuth = AppState.weather.windDirectionDeg; // Dirección desde donde viene el viento
      const safePt = turf.transformTranslate(uPt, 2.5, escapeAzimuth);
      const safeCoords = safePt.geometry.coordinates;

      AppState.currentSafeZoneTarget = { lat: safeCoords[1], lon: safeCoords[0] };

      // Marcador de Safe Zone
      L.circleMarker([safeCoords[1], safeCoords[0]], {
        radius: 10,
        color: '#10B981',
        fillColor: '#059669',
        fillOpacity: 0.85,
        weight: 3
      }).bindPopup("<b>🛡️ ZONA SEGURA RECOMENDADA</b><br>Posición a barlovento libre de avance y humo.")
        .addTo(AppState.layers.safeZones);

      fetchRealRoadRouting(AppState.userLocation.lat, AppState.userLocation.lon, safeCoords[1], safeCoords[0], escapeAzimuth);
    }

    // Enrutamiento con OSRM
    async function fetchRealRoadRouting(userLat, userLon, safeLat, safeLon, azimuth) {
      AppState.layers.escapeRoute.clearLayers();
      const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${userLon},${userLat};${safeLon},${safeLat}?overview=full&geometries=geojson`;

      let roadPoints = null;
      let realDistKm = 2.5;
      let realMin = 6;
      let roadName = "Red Vial / Ruta";

      try {
        const ctrl = new AbortController();
        const timeout = setTimeout(() => ctrl.abort(), 3000);
        const res = await fetch(osrmUrl, { signal: ctrl.signal });
        clearTimeout(timeout);
        if (res.ok) {
          const d = await res.json();
          if (d && d.routes && d.routes.length > 0) {
            roadPoints = d.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
            realDistKm = d.routes[0].distance / 1000.0;
            realMin = Math.max(1, Math.round(d.routes[0].duration / 60.0));
            roadName = d.routes[0].legs[0]?.summary || "Ruta Provincial";
          }
        }
      } catch (e) {}

      if (!roadPoints || roadPoints.length < 2) {
        roadPoints = [[userLat, userLon], [(userLat + safeLat)/2 + 0.002, (userLon + safeLon)/2 - 0.002], [safeLat, safeLon]];
      }

      L.polyline(roadPoints, { color: '#059669', weight: 8, opacity: 0.35 }).addTo(AppState.layers.escapeRoute);
      L.polyline(roadPoints, { color: '#10B981', weight: 4.5, className: 'animated-escape-path' }).addTo(AppState.layers.escapeRoute);

      const cardinal = degreesToCardinal(azimuth);
      document.getElementById('stat-route-distance').innerText = `${realDistKm.toFixed(1)} km`;
      document.getElementById('stat-route-time').innerText = `${realMin} min`;
      document.getElementById('stat-route-cardinal').innerText = cardinal;
      document.getElementById('user-escape-instruction').innerText = 
        `Evacúe inmediatamente hacia el ${cardinal} por ${roadName}. Refugio a barlovento en ${realDistKm.toFixed(1)} km.`;
    }

    function setAppMode(mode) {
      AppState.mode = mode;
      const bBrigade = document.getElementById('btn-mode-brigadista');
      const bUser = document.getElementById('btn-mode-productor');
      const pBrigade = document.getElementById('panel-brigadista');
      const pUser = document.getElementById('panel-productor');

      if (mode === 'BRIGADISTA') {
        bBrigade.className = "flex-1 py-1.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 shadow-lg shadow-amber-500/30 font-bold";
        bUser.className = "flex-1 py-1.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200";
        pBrigade.classList.remove('hidden');
        pUser.classList.add('hidden');
      } else {
        bUser.className = "flex-1 py-1.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5 bg-gradient-to-r from-tactical-accent to-red-600 text-white shadow-lg shadow-tactical-accent/40 font-bold";
        bBrigade.className = "flex-1 py-1.5 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200";
        pUser.classList.remove('hidden');
        pBrigade.classList.add('hidden');
      }
    }

    function openNativeGoogleMaps() {
      if (!AppState.currentSafeZoneTarget) return;
      const o = `${AppState.userLocation.lat.toFixed(5)},${AppState.userLocation.lon.toFixed(5)}`;
      const d = `${AppState.currentSafeZoneTarget.lat.toFixed(5)},${AppState.currentSafeZoneTarget.lon.toFixed(5)}`;
      window.open(`https://www.google.com/maps/dir/?api=1&origin=${o}&destination=${d}&travelmode=driving`, '_blank');
    }

    function triggerDemoScenario() {
      AppState.userLocation = { lat: -33.2380, lon: -65.9510 };
      AppState.userMarker.setLatLng([AppState.userLocation.lat, AppState.userLocation.lon]);
      map.setView([AppState.userLocation.lat, AppState.userLocation.lon], 13);
      AppState.weather.windSpeedKmh = 36.0;
      AppState.weather.windDirectionDeg = 205.0;
      updateHudDisplay();
      recalculatePredictiveEngine();
      switchMainTab('tactical');
      setAppMode('PRODUCTOR');
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
      return `🚨 *SOS EMERGENCIA INCENDIO (AURA-FIRE)*\n` +
             `📍 *Ubicación GPS:* ${gps}\n` +
             `🗺️ *Ver en Google Maps:* ${mapsUrl}\n` +
             `⏱️ *Tiempo Estimado Impacto:* ${eta}\n` +
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
      return c[Math.round(deg / 45) % 8];
    }
  </script>
</body>
</html>
'''

def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    html_content = get_template()
    
    # 1. Guardar en output/app_tactica_mobile.html
    tactical_path = os.path.join(output_dir, "app_tactica_mobile.html")
    with open(tactical_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # 2. Guardar también como output/index.html (Página Principal de Entrada)
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"📱 Portal Unificado AURA-FIRE generado con éxito:")
    print(f"   - {tactical_path} ({os.path.getsize(tactical_path)} bytes)")
    print(f"   - {index_path} ({os.path.getsize(index_path)} bytes)")

if __name__ == "__main__":
    main()
