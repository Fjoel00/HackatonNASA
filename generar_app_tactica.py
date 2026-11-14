#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
AURA-FIRE Unified Mission Control Portal Generator (NASA Space Apps 2026)
=============================================================================
Genera el portal web interactivo de misión crítica de grado aeroespacial:
1. 📅 BURNING ACTIVITY CALENDAR: Matriz de 52 semanas, línea base climatológica
   de 20 años, Z-Score de anomalía y factor de armonización de escala MODIS/VIIRS.
2. 🛰️ MONITOR SATELITAL NRT: Mapa interactivo con capas independientes para VIIRS (375m),
   MODIS (1km), frentes consolidados por DBSCAN geodésico y telemetría por satélite.
3. 🛡️ AURA-FIRE TÁCTICO & SUPERVIVENCIA: Centro de control dual (Brigadista / Evacuación),
   enrutamiento por carreteras con OSRM, clima en vivo Open-Meteo, conos Turf.js y SOS.
4. ⏱️ TIMELINE SCRUBBER: Reproducción temporal de pasadas satelitales NRT.
5. 🔬 SENSOR FOOTPRINT INSPECTOR: Comparador dinámico de resolución espacial (1km vs 375m).
"""

import os
import json

def get_template():
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
  <title>AURA-FIRE Mission Control | Harmonization of MODIS & VIIRS (NASA Space Apps)</title>
  
  <!-- Google Fonts: Inter & JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet">

  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
            mono: ['JetBrains Mono', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace']
          },
          colors: {
            tactical: {
              950: '#05070D',
              900: '#0B101D',
              850: '#10172A',
              800: '#162038',
              700: '#233256',
              600: '#334878',
              accent: '#FF4D2D',
              viirs: '#F59E0B',
              modis: '#EF4444',
              fused: '#FF5722',
              safe: '#10B981',
              warning: '#F59E0B',
              alert: '#EF4444',
              telemetry: '#06B6D4'
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
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      touch-action: manipulation;
      background-color: #05070D;
      color: #E2E8F0;
      overflow: hidden;
    }
    
    .font-mono-numbers {
      font-family: 'JetBrains Mono', monospace;
      font-feature-settings: "tnum" 1, "cv05" 1;
    }

    /* Glassmorphism Surface Tokens */
    .glass-surface {
      background: rgba(11, 16, 29, 0.88);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45);
    }
    .glass-surface-dense {
      background: rgba(8, 12, 22, 0.96);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .glass-inset {
      background: rgba(5, 7, 13, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.05);
    }

    #map {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      right: 0;
      width: 100%;
      height: 100%;
      z-index: 10;
      background: #05070D;
    }
    .leaflet-container {
      background: #05070D !important;
      width: 100%;
      height: 100%;
      font-family: inherit;
    }
    
    /* Pulso interactivo de usuario */
    .user-pulse-marker {
      width: 24px;
      height: 24px;
      background: #06B6D4;
      border: 3.5px solid #FFFFFF;
      border-radius: 50%;
      box-shadow: 0 0 20px #06B6D4;
      animation: pulse-user 2s cubic-bezier(0.24, 0, 0.38, 1) infinite;
      cursor: grab;
    }
    .user-pulse-marker:active {
      cursor: grabbing;
      transform: scale(1.15);
    }
    @keyframes pulse-user {
      0% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.8); }
      70% { box-shadow: 0 0 0 20px rgba(6, 182, 212, 0); }
      100% { box-shadow: 0 0 0 0 rgba(6, 182, 212, 0); }
    }

    /* Ruta de escape animada */
    .animated-escape-path {
      stroke-dasharray: 8, 8;
      animation: dash-flow 1.2s linear infinite;
    }
    @keyframes dash-flow {
      to { stroke-dashoffset: -16; }
    }

    /* Pulso de semana actual en calendario */
    .current-week-pulse {
      animation: border-pulse 2s infinite ease-in-out;
    }
    @keyframes border-pulse {
      0% { border-color: rgba(255, 77, 45, 0.5); box-shadow: 0 0 0 0 rgba(255, 77, 45, 0.7); }
      70% { border-color: rgba(255, 77, 45, 1); box-shadow: 0 0 0 8px rgba(255, 77, 45, 0); }
      100% { border-color: rgba(255, 77, 45, 0.5); box-shadow: 0 0 0 0 rgba(255, 77, 45, 0); }
    }

    /* Live Beacon Pulsing */
    .live-beacon {
      animation: live-glow 1.5s infinite;
    }
    @keyframes live-glow {
      0% { opacity: 0.4; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.2); }
      100% { opacity: 0.4; transform: scale(0.9); }
    }

    /* Scrollbars Tácticas */
    ::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    ::-webkit-scrollbar-track {
      background: rgba(5, 7, 13, 0.5);
    }
    ::-webkit-scrollbar-thumb {
      background: #233256;
      border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #334878;
    }

    /* Custom Leaflet Popups */
    .leaflet-popup-content-wrapper {
      background: rgba(11, 16, 29, 0.95) !important;
      backdrop-filter: blur(12px) !important;
      border: 1px solid rgba(255, 255, 255, 0.15) !important;
      border-radius: 12px !important;
      color: #E2E8F0 !important;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7) !important;
      padding: 0 !important;
    }
    .leaflet-popup-content {
      margin: 12px !important;
      line-height: 1.4 !important;
    }
    .leaflet-popup-tip {
      background: rgba(11, 16, 29, 0.95) !important;
    }
    .leaflet-container a.leaflet-popup-close-button {
      color: #94A3B8 !important;
      padding: 6px 6px 0 0 !important;
    }
    .leaflet-container a.leaflet-popup-close-button:hover {
      color: #FFFFFF !important;
    }

    /* Gauge Arc */
    .gauge-bg {
      stroke: #162038;
      stroke-width: 8;
      fill: none;
    }
    .gauge-fill {
      stroke-width: 8;
      fill: none;
      stroke-linecap: round;
      transition: stroke-dashoffset 0.8s ease-in-out;
    }
  </style>
</head>
<body class="bg-tactical-950 text-slate-100 h-full flex flex-col overflow-hidden select-none">

  <!-- ========================================================================= -->
  <!-- 1. NAVBAR DE COMANDO SUPERIOR: BRAND, TELEMETRÍA, TABS Y PRESETS         -->
  <!-- ========================================================================= -->
  <header class="glass-surface-dense border-b border-tactical-800/80 px-3 py-2 z-40 shrink-0">
    <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2.5">
      
      <!-- Brand & Mission Badge -->
      <div class="flex items-center gap-3">
        <div class="relative w-9 h-9 rounded-xl bg-gradient-to-br from-tactical-accent via-orange-600 to-red-600 flex items-center justify-center shadow-lg shadow-tactical-accent/30 text-white font-black">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path>
          </svg>
          <span class="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 border-2 border-tactical-950 live-beacon"></span>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-black tracking-widest uppercase text-white font-mono">AURA-FIRE</span>
            <span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-950/90 text-cyan-300 border border-cyan-500/40 font-mono font-bold tracking-tight">
              NASA SPACE APPS 2026
            </span>
            <span class="hidden sm:inline-flex items-center gap-1 text-[9px] text-emerald-400 font-mono font-semibold">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> NRT LIVE
            </span>
          </div>
          <div class="text-[10px] text-slate-400 font-mono flex items-center gap-1.5">
            <span class="text-slate-300 font-medium">Fusión MODIS & VIIRS</span>
            <span class="text-slate-600">|</span>
            <span id="label-region-info" class="text-amber-400 font-semibold truncate max-w-[200px] sm:max-w-none">Sierras de Córdoba / San Luis</span>
          </div>
        </div>
      </div>

      <!-- Segmented Navigation Pills -->
      <nav class="flex bg-tactical-950/90 p-1 rounded-xl border border-tactical-800 text-xs font-medium shadow-inner">
        <button id="tab-btn-calendar" onclick="switchMainTab('calendar')"
                class="view-tab-btn px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 bg-gradient-to-r from-tactical-accent to-orange-600 text-white shadow-md shadow-tactical-accent/25 font-bold">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
          <span class="hidden md:inline">Calendario de Quemas</span>
          <span class="md:hidden">Calendario</span>
        </button>
        <button id="tab-btn-monitor" onclick="switchMainTab('monitor')"
                class="view-tab-btn px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 text-slate-400 hover:text-slate-200">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m9.17 14.83-4.24 4.24"/></svg>
          <span>Monitor NRT</span>
        </button>
        <button id="tab-btn-tactical" onclick="switchMainTab('tactical')"
                class="view-tab-btn px-3 py-1.5 rounded-lg transition-all duration-200 flex items-center gap-1.5 text-slate-400 hover:text-slate-200">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          <span>AURA Táctico</span>
        </button>
      </nav>

      <!-- Region Selector & Preset Scenarios -->
      <div class="flex items-center gap-2">
        <select id="select-region" onchange="changeRegion(this.value)"
                class="bg-tactical-850 hover:bg-tactical-800 text-slate-200 text-xs font-mono py-1.5 px-2.5 rounded-xl border border-tactical-700 outline-none cursor-pointer transition-all">
          <option value="Sierras_Cordoba_SanLuis" selected>📍 Vista Regional: Córdoba y San Luis</option>
          <option value="Trapiche_SanLuis">🔥 Foco Crítico: El Trapiche / San Luis (Multi-Sensor)</option>
          <option value="Traslasierra_Cordoba">🔥 Foco Traslasierra: Mina Clavero / San Javier</option>
          <option value="Cordoba_SierrasChicas">🔥 Foco Sierras Chicas / Gran Córdoba</option>
        </select>

        <!-- Quick Demos -->
        <div class="hidden lg:flex items-center gap-1">
          <button onclick="triggerDemoScenario()" title="Simulación táctica en vivo"
                  class="flex items-center gap-1 text-[11px] bg-tactical-850 hover:bg-tactical-800 text-amber-300 px-2.5 py-1.5 rounded-xl border border-amber-500/40 font-mono shadow-md transition-all active:scale-95">
            <span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span> Demo Crítica
          </button>
        </div>

        <!-- Audio Alert Mute Toggle -->
        <button id="btn-audio-toggle" onclick="toggleTacticalAudio()" title="Activar/Silenciar Alerta Acústica de Misión"
                class="bg-tactical-850 hover:bg-tactical-800 text-slate-300 p-1.5 rounded-xl border border-tactical-700 text-xs transition-all">
          <span id="audio-icon">🔊</span>
        </button>

        <!-- Mission Info Modal Button -->
        <button onclick="openMissionModal()" title="Fundamento Científico y Guía del Reto"
                class="bg-tactical-850 hover:bg-tactical-800 text-cyan-400 p-1.5 rounded-xl border border-cyan-500/30 text-xs font-mono font-bold transition-all">
          ?
        </button>
      </div>

    </div>
  </header>

  <!-- ========================================================================= -->
  <!-- 2. VISTA 1: BURNING ACTIVITY CALENDAR & CLIMATOLOGÍA HISTÓRICA            -->
  <!-- ========================================================================= -->
  <section id="view-calendar" class="view-tab flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
    <div class="max-w-7xl mx-auto space-y-6">
      
      <!-- Hero Banner -->
      <div class="glass-surface rounded-2xl p-5 border border-tactical-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 text-xs text-tactical-accent font-mono font-bold uppercase tracking-wider">
            <span>NASA Space Apps Challenge</span>
            <span>•</span>
            <span>Harmonization of MODIS & VIIRS Hot Spots</span>
          </div>
          <h1 class="text-xl sm:text-2xl font-black text-white mt-1 tracking-tight">
            Burning Activity Calendar & Régimen Climatológico Anual
          </h1>
          <p class="text-xs sm:text-sm text-slate-300 max-w-3xl mt-1.5 leading-relaxed">
            Reconstrucción de la serie histórica continua (2000–2026) compensando la divergencia física entre <b>MODIS (1 km)</b> y <b>VIIRS (375 m)</b> mediante función de transferencia geométrica, normalización de densidad radiativa (<span class="font-mono text-cyan-400">MW/km²</span>) y monitoreo de desvío estacional Z-Score.
          </p>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <div class="text-right glass-inset px-4 py-2.5 rounded-xl border border-tactical-700">
            <div class="text-[10px] text-slate-400 font-mono uppercase">Régimen Estacional</div>
            <div id="cal-kpi-risk-label" class="text-sm font-black text-amber-400 font-mono">FIN DE TEMPORADA SECA</div>
            <div id="cal-kpi-risk-index" class="text-[11px] text-slate-400 font-mono">Riesgo Climático: 35%</div>
          </div>
        </div>
      </div>

      <!-- Métricas Clave de Armonización -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        
        <div class="glass-surface rounded-2xl p-4 border border-tactical-800">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Semana Actual</span>
            <span class="text-cyan-400">📅</span>
          </div>
          <div id="cal-stat-current-week" class="text-2xl font-black font-mono-numbers text-white mt-1">
            Semana 46
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            Mes de Noviembre (Ciclo Anual 1-52)
          </div>
        </div>

        <div class="glass-surface rounded-2xl p-4 border border-tactical-800">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Anomalía Z-Score</span>
            <span class="text-amber-400">📊</span>
          </div>
          <div id="cal-stat-zscore" class="text-2xl font-black font-mono-numbers text-emerald-400 mt-1">
            -0.45 σ
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            Dentro del promedio climatológico histórico
          </div>
        </div>

        <div class="glass-surface rounded-2xl p-4 border border-tactical-800">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Focos Armonizados</span>
            <span class="text-orange-400">🛰️</span>
          </div>
          <div id="cal-stat-harmonized-hotspots" class="text-2xl font-black font-mono-numbers text-amber-400 mt-1">
            45.0 eq
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            31 crudos (28 VIIRS + 3 MODIS escalados 4.0x)
          </div>
        </div>

        <div class="glass-surface rounded-2xl p-4 border border-tactical-800">
          <div class="text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Energía Radiativa (FRE)</span>
            <span class="text-red-400">⚡</span>
          </div>
          <div id="cal-stat-fre" class="text-2xl font-black font-mono-numbers text-tactical-accent mt-1">
            2.91 GJ
          </div>
          <div class="text-[10px] text-slate-400 mt-1">
            Integral de FRP por sobrepasos temporales
          </div>
        </div>

      </div>

      <!-- Matriz de 52 Semanas -->
      <div class="glass-surface rounded-2xl p-5 border border-tactical-800 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-tactical-800/80 pb-3">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-tactical-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
              <span>Matriz de Actividad Anual por Semanas Ecológicas (1 a 52)</span>
            </h2>
            <p class="text-xs text-slate-400">
              Seleccione cualquier semana para contrastar las anomalías satelitales respecto a la línea base de 20 años de NASA FIRMS.
            </p>
          </div>
          
          <!-- Leyenda de Niveles -->
          <div class="flex items-center gap-2 text-[10px] font-mono flex-wrap bg-tactical-950/80 px-3 py-1.5 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Niveles:</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-slate-800 border border-slate-700"></span> Inactivo</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#fee08b]"></span> Bajo</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#fdae61]"></span> Normal</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#f46d43]"></span> Alto</span>
            <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-sm bg-[#d73027]"></span> Crítico</span>
          </div>
        </div>

        <!-- Grilla agrupada por Mes -->
        <div id="cal-weeks-grid" class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2.5 overflow-x-auto pb-2">
          <!-- Inyectado dinámicamente con JS -->
        </div>

        <!-- Tarjeta de Detalle de Semana Seleccionada -->
        <div id="cal-week-detail-card" class="glass-inset rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-tactical-700/60">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span id="detail-week-badge" class="px-2 py-0.5 rounded-md bg-tactical-accent/20 text-tactical-accent font-mono font-bold text-xs border border-tactical-accent/30">Semana 46</span>
              <span id="detail-month-label" class="text-xs text-slate-200 font-semibold">Mes de Noviembre</span>
              <span id="detail-status-pill" class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-600/40 font-mono">Normal / Dentro del promedio</span>
            </div>
            <div id="detail-summary-text" class="text-xs text-slate-300">
              Línea base histórica: 141.5 focos esperados en Noviembre. Actividad registrada: 45.0 focos equivalentes armonizados.
            </div>
          </div>
          <div class="flex items-center gap-4 text-xs font-mono shrink-0">
            <div>
              <div class="text-[10px] text-slate-400 uppercase">Focos Observados</div>
              <div id="detail-observed-val" class="text-sm font-bold text-white font-mono-numbers">45.0 eq</div>
            </div>
            <div class="h-8 w-px bg-tactical-800"></div>
            <div>
              <div class="text-[10px] text-slate-400 uppercase">Media Histórica</div>
              <div id="detail-baseline-val" class="text-sm font-bold text-slate-300 font-mono-numbers">35.4 focos</div>
            </div>
            <div class="h-8 w-px bg-tactical-800"></div>
            <div>
              <div class="text-[10px] text-slate-400 uppercase">Potencia Radiativa</div>
              <div id="detail-frp-val" class="text-sm font-bold text-tactical-accent font-mono-numbers">456.7 MW</div>
            </div>
          </div>
        </div>

      </div>

      <!-- Curva Climatológica SVG Interactiva -->
      <div class="glass-surface rounded-2xl p-5 border border-tactical-800 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-tactical-800/80 pb-3">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
              <span>Tendencia Estacional: Línea Base Histórica vs. Observación 2026</span>
            </h2>
            <p class="text-xs text-slate-400">
              Banda climatológica de desviación estándar ($\pm 1\sigma$) contrastada con las detecciones satelitales armonizadas en tiempo real.
            </p>
          </div>
          <div class="flex items-center gap-3 text-[11px] font-mono bg-tactical-950/80 px-3 py-1.5 rounded-xl border border-tactical-800">
            <span class="flex items-center gap-1.5"><span class="w-3 h-0.5 bg-cyan-400 inline-block"></span> Media Histórica</span>
            <span class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 rounded-full bg-tactical-accent inline-block"></span> Observación Actual</span>
          </div>
        </div>

        <!-- Contenedor del Gráfico SVG con Tooltip -->
        <div class="relative w-full h-64 glass-inset rounded-xl p-2 border border-tactical-800">
          <svg id="cal-seasonal-chart" class="w-full h-full" viewBox="0 0 800 240" preserveAspectRatio="none">
            <!-- Renderizado dinámicamente con JS -->
          </svg>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div class="glass-inset p-3 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Período Crítico Histórico:</span>
            <div class="text-amber-400 font-bold font-mono mt-0.5" id="cal-info-peak-period">Agosto – Octubre (Semanas 31 a 44)</div>
          </div>
          <div class="glass-inset p-3 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Función de Transferencia de Escala:</span>
            <div class="text-cyan-400 font-bold font-mono mt-0.5">Hotspot_eq = Conteo × 4.0 · √(Área / 1.0)</div>
          </div>
          <div class="glass-inset p-3 rounded-xl border border-tactical-800">
            <span class="text-slate-400">Ratio Empírico de Resolución:</span>
            <div class="text-emerald-400 font-bold font-mono mt-0.5" id="cal-info-ratio">VIIRS / MODIS ≈ 9.33x en escena</div>
          </div>
        </div>

      </div>

    </div>
  </section>

  <!-- ========================================================================= -->
  <!-- 3. VISTA 2 & 3: MAPA COMANDADO, SIDEBAR DOCKABLE Y SCRUBBER TEMPORAL     -->
  <!-- ========================================================================= -->
  <div id="view-map-container" class="view-tab flex-1 relative overflow-hidden hidden flex flex-col">
    
    <!-- BANNER DINÁMICO DE ESTADO (MÁQUINA DE ESTADOS FSM) -->
    <div id="fsm-banner" class="bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white px-4 py-2 border-b border-red-500/50 flex items-center justify-between shrink-0 shadow-xl transition-all duration-300 z-30">
      <div class="flex items-center gap-3">
        <div id="fsm-icon" class="text-xl">🚨</div>
        <div>
          <div id="fsm-status-title" class="text-xs font-black uppercase tracking-wider font-mono">
            IMPACTO INMINENTE — ZONA ROJA
          </div>
          <div id="fsm-status-desc" class="text-[11px] text-red-100 font-medium">
            Frente de fuego avanzando hacia su ubicación. Evacúe de inmediato por la ruta marcada.
          </div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <div class="text-right bg-black/40 px-3 py-1 rounded-xl border border-white/20">
          <div class="text-[9px] uppercase tracking-wider text-red-200 font-mono">Tiempo de Impacto</div>
          <div id="fsm-eta-display" class="text-lg font-mono-numbers font-black tracking-tight text-white">
            -- MIN
          </div>
        </div>
      </div>
    </div>

    <!-- BARRA HUD METEOROLÓGICA (OPEN-METEO) -->
    <div id="hud-bar" class="glass-surface-dense border-b border-tactical-800/80 px-3 py-1.5 text-[11px] font-mono flex items-center justify-between overflow-x-auto gap-4 shrink-0 z-20">
      <div class="flex items-center gap-3 whitespace-nowrap">
        <div class="flex items-center gap-1.5">
          <span class="text-slate-400">💨 Viento:</span>
          <span id="hud-wind-speed" class="text-amber-300 font-bold font-mono-numbers">-- km/h</span>
          <span id="hud-wind-arrow" class="inline-block transition-transform duration-500 text-amber-400 font-bold">↑</span>
          <span id="hud-wind-dir" class="text-slate-300 font-mono-numbers">--°</span>
        </div>
        <div class="h-3 w-px bg-tactical-800"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">🌡️ Temp:</span>
          <span id="hud-temp" class="text-slate-200 font-mono-numbers">--°C</span>
        </div>
        <div class="h-3 w-px bg-tactical-800"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">💧 HR:</span>
          <span id="hud-humidity" class="text-slate-200 font-mono-numbers">--%</span>
        </div>
        <div class="h-3 w-px bg-tactical-800"></div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">🔥 FRP Pico:</span>
          <span id="hud-frp" class="text-tactical-accent font-bold font-mono-numbers">-- MW</span>
        </div>
      </div>

      <!-- Badge 30-30-30 -->
      <div id="badge-crossover" class="hidden px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-700/60 text-[10px] font-bold uppercase tracking-wider animate-pulse whitespace-nowrap">
        ⚠️ CONDICIÓN EXTREMA 30-30-30
      </div>
    </div>

    <!-- MAIN MAP AREA WITH DOCKABLE SIDEBAR -->
    <div class="flex-1 relative overflow-hidden flex">
      
      <!-- MAP CONTAINER -->
      <div id="map" class="flex-1"></div>

      <!-- FLOATING COMPASS & WIND VECTOR -->
      <div class="absolute top-4 right-4 z-20 pointer-events-none hidden sm:flex flex-col items-center gap-1">
        <div class="glass-surface p-2 rounded-2xl border border-tactical-700 pointer-events-auto shadow-2xl flex flex-col items-center">
          <div class="text-[9px] font-mono text-slate-400 uppercase font-bold">RUMBO VIENTO</div>
          <div class="relative w-12 h-12 flex items-center justify-center my-1">
            <!-- Compass Rose Circle -->
            <div class="absolute inset-0 rounded-full border border-tactical-700 border-dashed"></div>
            <div class="absolute top-0 text-[8px] font-mono text-slate-500 font-bold">N</div>
            <div class="absolute bottom-0 text-[8px] font-mono text-slate-500 font-bold">S</div>
            <div class="absolute right-0 text-[8px] font-mono text-slate-500 font-bold">E</div>
            <div class="absolute left-0 text-[8px] font-mono text-slate-500 font-bold">W</div>
            <!-- Wind Arrow Pointer -->
            <div id="floating-compass-arrow" class="w-1 h-8 bg-gradient-to-t from-transparent via-amber-500 to-red-500 rounded-full origin-center transition-transform duration-700"></div>
          </div>
          <div id="floating-wind-cardinal" class="text-[10px] font-mono font-bold text-amber-400">SSW</div>
        </div>
      </div>

      <!-- SIDEBAR TOGGLE BUTTON (COLLAPSE/EXPAND) -->
      <button id="btn-sidebar-toggle" onclick="toggleSidebar()"
              class="absolute top-4 left-4 z-30 glass-surface hover:bg-tactical-800 text-slate-200 p-2 rounded-xl border border-tactical-700 shadow-2xl transition-all duration-300 flex items-center gap-1.5 text-xs font-mono">
        <span id="sidebar-toggle-icon">◀</span>
        <span id="sidebar-toggle-text" class="hidden sm:inline font-bold">PANEL TÁCTICO</span>
      </button>

      <!-- DOCKABLE MISSION CONTROL SIDEBAR -->
      <aside id="mission-sidebar" class="absolute top-14 bottom-4 left-4 w-96 max-w-[calc(100vw-2rem)] glass-surface rounded-2xl border border-tactical-700 z-20 flex flex-col shadow-2xl transition-all duration-300 overflow-hidden">
        
        <!-- Sidebar Navigation Tabs -->
        <div class="flex border-b border-tactical-800/80 p-1.5 bg-tactical-950/70 gap-1 text-[11px] font-mono shrink-0">
          <button id="sb-tab-clusters" onclick="setSidebarTab('clusters')"
                  class="flex-1 py-1.5 px-2 rounded-lg transition-all text-center bg-tactical-accent text-white font-bold">
            Frentes
          </button>
          <button id="sb-tab-inspector" onclick="setSidebarTab('inspector')"
                  class="flex-1 py-1.5 px-2 rounded-lg transition-all text-center text-slate-400 hover:text-white">
            Sensores
          </button>
          <button id="sb-tab-weather" onclick="setSidebarTab('weather')"
                  class="flex-1 py-1.5 px-2 rounded-lg transition-all text-center text-slate-400 hover:text-white">
            Clima
          </button>
          <button id="sb-tab-escape" onclick="setSidebarTab('escape')"
                  class="flex-1 py-1.5 px-2 rounded-lg transition-all text-center text-slate-400 hover:text-white">
            Escape & SOS
          </button>
        </div>

        <!-- Sidebar Tab 1: Frentes de Fuego (Clusters) -->
        <div id="sb-content-clusters" class="sidebar-pane flex-1 overflow-y-auto p-3.5 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-1.5">
              <span>🛰️</span> Frentes Activos (DBSCAN)
            </span>
            <span id="badge-clusters-count" class="text-[10px] px-2 py-0.5 rounded-full bg-tactical-800 text-slate-300 font-mono">
              8 frentes
            </span>
          </div>

          <!-- Cluster List -->
          <div id="sidebar-cluster-list" class="space-y-2">
            <!-- Dynamic cluster list -->
          </div>
        </div>

        <!-- Sidebar Tab 2: Sensor Footprint Inspector (Comparador Físico) -->
        <div id="sb-content-inspector" class="sidebar-pane flex-1 overflow-y-auto p-3.5 space-y-3 hidden">
          <div class="flex items-center justify-between border-b border-tactical-800 pb-2">
            <span class="text-xs font-bold text-white uppercase tracking-wider font-mono">
              🔬 Inspector de Huella de Sensores
            </span>
            <span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-950 text-cyan-300 border border-cyan-500/40 font-mono">
              Resolución Espacial
            </span>
          </div>

          <p class="text-[11px] text-slate-300 leading-relaxed">
            Divergencia física entre el píxel de <b>MODIS (1.0 km²)</b> y <b>VIIRS (0.14 km²)</b>. Haga clic en cualquier foco térmico del mapa para inspeccionar sus características espectrales.
          </p>

          <!-- Visual Footprint Comparison Box -->
          <div class="glass-inset rounded-xl p-3 border border-tactical-800 space-y-2">
            <div class="text-[10px] font-mono text-slate-400 uppercase">Escala Relativa de Huella de Detección:</div>
            
            <div class="relative w-full h-32 bg-tactical-950 rounded-lg border border-tactical-800 flex items-center justify-center p-2 overflow-hidden">
              <!-- MODIS Footprint (1km x 1km) -->
              <div class="w-28 h-28 border-2 border-red-500 bg-red-500/15 rounded flex items-start justify-start p-1 relative">
                <span class="text-[9px] font-mono text-red-400 font-bold">MODIS: 1.00 km² (1000m)</span>
                
                <!-- VIIRS Footprint (375m x 375m) in scale -->
                <div class="absolute bottom-1 right-1 w-11 h-11 border-2 border-amber-400 bg-amber-400/30 rounded flex items-center justify-center">
                  <span class="text-[8px] font-mono text-amber-300 font-bold text-center leading-none">VIIRS<br>0.14 km²</span>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2 text-[10px] font-mono pt-1">
              <div class="bg-tactical-900 p-2 rounded-lg border border-tactical-800">
                <div class="text-amber-400 font-bold">VIIRS (375 m)</div>
                <div class="text-slate-400">Canal $T_{I4}$: 3.74 µm</div>
                <div class="text-slate-400">Canal $T_{I5}$: 11.45 µm</div>
              </div>
              <div class="bg-tactical-900 p-2 rounded-lg border border-tactical-800">
                <div class="text-red-400 font-bold">MODIS (1000 m)</div>
                <div class="text-slate-400">Canal $T_{21/22}$: 3.96 µm</div>
                <div class="text-slate-400">Canal $T_{31}$: 11.03 µm</div>
              </div>
            </div>
          </div>

          <!-- Hotspot Inspector Card -->
          <div id="inspector-hotspot-card" class="glass-inset rounded-xl p-3 border border-tactical-800 space-y-2 text-xs font-mono">
            <div class="flex items-center justify-between text-slate-300">
              <span class="font-bold">Foco Seleccionado:</span>
              <span id="insp-sensor-family" class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[10px]">VIIRS 375m</span>
            </div>
            <div class="space-y-1 text-[11px] text-slate-300">
              <div class="flex justify-between">
                <span class="text-slate-400">Satélite:</span>
                <span id="insp-satellite" class="font-bold text-white">NOAA-20</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Potencia FRP:</span>
                <span id="insp-frp" class="font-bold text-tactical-accent font-mono-numbers">45.2 MW</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Densidad Radiativa:</span>
                <span id="insp-frp-density" class="font-bold text-cyan-400 font-mono-numbers">321.4 MW/km²</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Temp. Brillo (4µm):</span>
                <span id="insp-temp-ch4" class="font-bold text-white font-mono-numbers">367.0 K</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Diferencial Térmico (ΔT):</span>
                <span id="insp-delta-t" class="font-bold text-amber-300 font-mono-numbers">42.5 K</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Nivel de Confianza:</span>
                <span id="insp-confidence" class="font-bold text-emerald-400">Alta (High)</span>
              </div>
            </div>
          </div>

        </div>

        <!-- Sidebar Tab 3: Dinámica & Meteorología -->
        <div id="sb-content-weather" class="sidebar-pane flex-1 overflow-y-auto p-3.5 space-y-3 hidden">
          <div class="flex items-center justify-between border-b border-tactical-800 pb-2">
            <span class="text-xs font-bold text-white uppercase tracking-wider font-mono">
              💨 Dinámica & Meteorología
            </span>
            <span class="text-[9px] px-1.5 py-0.5 rounded bg-tactical-800 text-slate-300 font-mono">
              Open-Meteo API
            </span>
          </div>

          <!-- Weather Widgets -->
          <div class="grid grid-cols-2 gap-2 text-xs font-mono">
            <div class="glass-inset p-3 rounded-xl border border-tactical-800">
              <span class="text-[10px] text-slate-400 uppercase">Velocidad Viento</span>
              <div id="weather-wind-speed" class="text-lg font-bold text-amber-300 font-mono-numbers mt-0.5">32 km/h</div>
              <div class="text-[9px] text-slate-500 mt-1">Ráfagas hasta 45 km/h</div>
            </div>
            <div class="glass-inset p-3 rounded-xl border border-tactical-800">
              <span class="text-[10px] text-slate-400 uppercase">Dirección (Origen)</span>
              <div id="weather-wind-dir" class="text-lg font-bold text-slate-200 font-mono-numbers mt-0.5">200° (SSW)</div>
              <div class="text-[9px] text-slate-500 mt-1">Hacia NNE (sotavento)</div>
            </div>
            <div class="glass-inset p-3 rounded-xl border border-tactical-800">
              <span class="text-[10px] text-slate-400 uppercase">Temperatura</span>
              <div id="weather-temp" class="text-lg font-bold text-slate-200 font-mono-numbers mt-0.5">33.5 °C</div>
              <div class="text-[9px] text-slate-500 mt-1">Estrés térmico alto</div>
            </div>
            <div class="glass-inset p-3 rounded-xl border border-tactical-800">
              <span class="text-[10px] text-slate-400 uppercase">Humedad Relativa</span>
              <div id="weather-humidity" class="text-lg font-bold text-red-400 font-mono-numbers mt-0.5">18.0 %</div>
              <div class="text-[9px] text-slate-500 mt-1">Condición crítica desecante</div>
            </div>
          </div>

          <!-- Regla 30-30-30 Alert Box -->
          <div class="bg-red-950/60 p-3 rounded-xl border border-red-700/60 space-y-1">
            <div class="flex items-center gap-2 text-red-400 font-bold font-mono text-xs">
              <span>⚠️</span>
              <span>ALERTA EXTREMA: CRUCE REGLA 30-30-30</span>
            </div>
            <p class="text-[11px] text-red-200/90 leading-tight">
              Temperatura &gt; 30°C, Viento &gt; 30 km/h y Humedad &lt; 30%. Probabilidad de comportamiento eruptivo y saltos de fuego por pavesas.
            </p>
          </div>

        </div>

        <!-- Sidebar Tab 4: Escape & SOS -->
        <div id="sb-content-escape" class="sidebar-pane flex-1 overflow-y-auto p-3.5 space-y-3 hidden">
          
          <!-- Mode Switcher: Brigadista vs Productor/Evacuación -->
          <div class="flex bg-tactical-950 p-1 rounded-xl border border-tactical-800 text-xs font-semibold shadow-inner">
            <button id="btn-mode-brigadista" onclick="setAppMode('BRIGADISTA')"
                    class="flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200">
              <span>🚒</span> Brigadista
            </button>
            <button id="btn-mode-productor" onclick="setAppMode('PRODUCTOR')"
                    class="flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 bg-gradient-to-r from-tactical-accent to-red-600 text-white shadow-md font-bold">
              <span>🏃</span> Evacuación
            </button>
          </div>

          <!-- Panel Brigadista -->
          <div id="panel-brigadista" class="hidden space-y-3">
            <div class="glass-inset p-3 rounded-xl border border-tactical-800 space-y-2 text-xs font-mono">
              <div class="flex justify-between items-center border-b border-tactical-800 pb-1.5">
                <span class="text-amber-400 font-bold uppercase">🚒 Telemetría de Frente</span>
                <span id="brigade-selected-cluster" class="text-[10px] px-2 py-0.5 rounded bg-tactical-800 text-slate-300">CLUSTER_001</span>
              </div>
              <div class="grid grid-cols-2 gap-2 text-xs pt-1">
                <div>
                  <div class="text-[10px] text-slate-400">Superficie Activa:</div>
                  <div id="brigade-area" class="text-sm font-bold text-amber-300 font-mono-numbers">47.1 ha</div>
                </div>
                <div>
                  <div class="text-[10px] text-slate-400">Velocidad Avance:</div>
                  <div id="brigade-sat-speed" class="text-sm font-bold text-tactical-accent font-mono-numbers">3.4 km/h</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Panel Productor / Evacuación -->
          <div id="panel-productor" class="space-y-3">
            <div class="glass-inset p-3 rounded-xl border border-tactical-800 space-y-2 text-xs">
              <div class="flex items-center justify-between border-b border-tactical-800 pb-1.5">
                <span class="font-mono text-xs font-bold text-emerald-400 uppercase flex items-center gap-1">
                  <span>🛣️</span> RUTA DE ESCAPE VIAL (OSRM)
                </span>
                <span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-600/40 font-mono">
                  Segura
                </span>
              </div>
              
              <div class="grid grid-cols-3 gap-2 py-1 font-mono text-center">
                <div class="bg-tactical-950 p-2 rounded-lg border border-tactical-800">
                  <div class="text-[9px] text-slate-400">Distancia</div>
                  <div id="stat-route-distance" class="text-xs font-bold text-white font-mono-numbers">-- km</div>
                </div>
                <div class="bg-tactical-950 p-2 rounded-lg border border-tactical-800">
                  <div class="text-[9px] text-slate-400">Tiempo</div>
                  <div id="stat-route-time" class="text-xs font-bold text-emerald-400 font-mono-numbers">-- min</div>
                </div>
                <div class="bg-tactical-950 p-2 rounded-lg border border-tactical-800">
                  <div class="text-[9px] text-slate-400">Rumbo</div>
                  <div id="stat-route-cardinal" class="text-xs font-bold text-amber-400">--</div>
                </div>
              </div>

              <p id="user-escape-instruction" class="text-[11px] text-slate-300 leading-snug">
                Calculando ruta transitable en dirección a barlovento...
              </p>
            </div>

            <!-- Botones de Acción -->
            <div class="grid grid-cols-2 gap-2">
              <button onclick="openNativeGoogleMaps()"
                      class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-blue-600/30 transition-all active:scale-95">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>
                <span>Abrir en Maps</span>
              </button>
              <button onclick="openSosModal()"
                      class="bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-black py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-red-600/40 transition-all active:scale-95 animate-pulse">
                <span>🚨</span> PEDIR AUXILIO
              </button>
            </div>
          </div>

        </div>

      </aside>

      <!-- TIMELINE / SATELLITE PASS SCRUBBER (FLOATING AT BOTTOM) -->
      <div class="absolute bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-[480px] z-20 glass-surface rounded-2xl border border-tactical-700/80 p-3 shadow-2xl space-y-2">
        <div class="flex items-center justify-between text-xs font-mono">
          <div class="flex items-center gap-2">
            <button id="btn-timeline-play" onclick="toggleTimelinePlay()"
                    class="w-7 h-7 rounded-lg bg-tactical-accent hover:bg-orange-600 text-white flex items-center justify-center font-bold transition-all shadow-md">
              <span id="play-icon">▶</span>
            </button>
            <span class="font-bold text-white">Línea Temporal Satelital</span>
          </div>
          <div id="timeline-pass-label" class="text-cyan-400 font-bold text-[11px]">
            Todas las Pasadas (NRT)
          </div>
        </div>

        <div class="flex items-center gap-3">
          <input id="timeline-slider" type="range" min="0" max="10" value="10" step="1" oninput="onTimelineSliderChange(this.value)"
                 class="w-full h-1.5 bg-tactical-800 rounded-lg appearance-none cursor-pointer accent-tactical-accent">
          <span id="timeline-step-badge" class="text-[10px] font-mono text-slate-400 shrink-0">10/10</span>
        </div>
      </div>

    </div>

  </div>

  <!-- ========================================================================= -->
  <!-- 4. MODAL: SOS DE EMERGENCIA CON QR & DESPACHO DIRECTO                     -->
  <!-- ========================================================================= -->
  <div id="modal-sos" class="hidden fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
    <div class="glass-surface-dense border border-red-500/80 rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-2xl">
      <div class="flex items-center justify-between border-b border-tactical-800 pb-3">
        <div class="flex items-center gap-2">
          <span class="text-2xl animate-bounce">🚨</span>
          <div>
            <h3 class="text-sm font-black text-white uppercase tracking-wider font-mono">Despacho SOS de Emergencia</h3>
            <div class="text-[10px] text-red-400 font-mono">Baliza Táctica de Misión AURA-FIRE</div>
          </div>
        </div>
        <button onclick="closeSosModal()" class="text-slate-400 hover:text-white text-lg font-bold">✕</button>
      </div>

      <div class="text-xs text-slate-300 space-y-2 font-mono glass-inset p-3.5 rounded-xl border border-tactical-800">
        <div><b>📍 GPS Decimal:</b> <span id="sos-gps-text" class="text-cyan-400 font-mono-numbers">--</span></div>
        <div><b>🧭 GPS Sexagesimal:</b> <span id="sos-dms-text" class="text-slate-300 font-mono-numbers">--</span></div>
        <div><b>⏱️ Tiempo Estimado Impacto:</b> <span id="sos-eta-text" class="text-red-400 font-bold font-mono-numbers">-- min</span></div>
        <div><b>💨 Viento en Zona:</b> <span id="sos-wind-text" class="text-amber-300 font-mono-numbers">--</span></div>
      </div>

      <div class="flex items-center justify-center p-2 bg-white rounded-xl shadow-inner">
        <!-- Dynamic QR Server rendering location link -->
        <img id="sos-qr-image" class="w-32 h-32" src="" alt="QR Localización SOS">
      </div>
      <div class="text-[10px] text-center text-slate-400 font-mono">
        Escanee para abrir coordenadas en cualquier dispositivo móvil
      </div>

      <div class="grid grid-cols-2 gap-2 pt-1">
        <button onclick="sendSosWhatsApp()"
                class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/30 transition-all">
          <span>💬</span> WhatsApp SOS
        </button>
        <button onclick="sendSosSms()"
                class="bg-red-600 hover:bg-red-500 text-white font-bold py-2.5 px-3 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-red-600/30 transition-all">
          <span>📱</span> SMS Satelital
        </button>
      </div>
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- 5. MODAL: ACERCA DEL DESAFÍO NASA SPACE APPS (MISSION BRIEFING)           -->
  <!-- ========================================================================= -->
  <div id="modal-mission" class="hidden fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
    <div class="glass-surface-dense border border-tactical-700 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-tactical-800 pb-3">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-tactical-accent flex items-center justify-center text-white font-bold">🚀</div>
          <div>
            <h3 class="text-base font-black text-white uppercase tracking-wider font-mono">NASA Space Apps Challenge 2026</h3>
            <div class="text-xs text-cyan-400 font-mono">Harmonization of MODIS & VIIRS Hot Spots</div>
          </div>
        </div>
        <button onclick="closeMissionModal()" class="text-slate-400 hover:text-white text-lg font-bold">✕</button>
      </div>

      <div class="text-xs text-slate-300 space-y-3 leading-relaxed">
        <div class="bg-tactical-950 p-3 rounded-xl border border-tactical-800 space-y-1">
          <b class="text-amber-400 font-mono">📌 1. El Desafío Físico de Integración</b>
          <p>
            Los sensores <b>MODIS</b> (a bordo de Terra y Aqua) operan a <b>1000 metros de resolución espacial</b> ($1.0\text{ km}^2$), mientras que <b>VIIRS</b> (a bordo de Suomi-NPP, NOAA-20 y NOAA-21) detecta anomalías térmicas a <b>375 metros</b> ($\approx 0.14\text{ km}^2$). Un incendio detectado por VIIRS genera hasta 9 veces más puntos que MODIS para la misma fogata.
          </p>
        </div>

        <div class="bg-tactical-950 p-3 rounded-xl border border-tactical-800 space-y-1">
          <b class="text-cyan-400 font-mono">🔬 2. Solución Científica Implementada en AURA-FIRE</b>
          <p>
            - <b>Normalización Espectral:</b> Unificación de canales de $4\,\mu\text{m}$ ($T_{21/22}$ y $T_{I4}$) y $11\,\mu\text{m}$ ($T_{31}$ y $T_{I5}$), junto con el cálculo del diferencial de combustión ($\Delta T = T_4 - T_5$).<br>
            - <b>Densidad Radiativa:</b> Estimación de la huella dinámica de píxel (`scan × track`) y cálculo de FRP Density en $\text{MW/km}^2$.<br>
            - <b>DBSCAN Geodésico:</b> Reconstrucción de frentes reales mediante clustering Haversine ($R = 6371\text{ km}, \varepsilon = 2.5\text{ km}$), cálculo de área convexa y vector de avance cinematográfico.
          </p>
        </div>

        <div class="bg-tactical-950 p-3 rounded-xl border border-tactical-800 space-y-1">
          <b class="text-emerald-400 font-mono">🛡️ 3. Impacto Operativo y Humanitario</b>
          <p>
            AURA-FIRE traduce datos satelitales en decisiones de vida o muerte: cálculo de ruta de evacuación por red vial transitable (OSRM) en dirección a barlovento y despacho SOS con código QR para brigadistas y productores agropecuarios.
          </p>
        </div>
      </div>

      <div class="text-right pt-2">
        <button onclick="closeMissionModal()"
                class="bg-tactical-850 hover:bg-tactical-800 text-slate-200 px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all border border-tactical-700">
          Entendido / Cerrar
        </button>
      </div>
    </div>
  </div>

  <!-- ========================================================================= -->
  <!-- 6. JAVASCRIPT DE CONTROL Y TELEMETRÍA CENTRAL                             -->
  <!-- ========================================================================= -->
  <script>
    window.PRELOADED_DASHBOARD_DATA = ''' + json_str + r''';

    const AppState = {
      currentTab: 'calendar',
      sidebarTab: 'clusters',
      sidebarOpen: true,
      mode: 'PRODUCTOR',
      audioEnabled: true,
      audioCtx: null,
      dashboardData: window.PRELOADED_DASHBOARD_DATA,
      selectedCluster: null,
      selectedHotspot: null,
      userLocation: { lat: -33.2380, lon: -65.9510 },
      userMarker: null,
      timelinePlaying: false,
      timelineTimer: null,
      timelineCurrentIndex: 10,
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
      currentSafeZoneTarget: null
    };

    let map = null;

    window.addEventListener('DOMContentLoaded', async () => {
      renderCalendar();
      initMap();
      loadActiveFireData();
      initTimelineScrubber();
      await fetchRealWeather();
      recalculatePredictiveEngine();
      switchMainTab('calendar');
    });

    // Conmutador de Pestañas Principales
    function switchMainTab(tabName) {
      AppState.currentTab = tabName;
      document.querySelectorAll('.view-tab-btn').forEach(btn => {
        btn.classList.remove('bg-gradient-to-r', 'from-tactical-accent', 'to-orange-600', 'text-white', 'shadow-md', 'font-bold');
        btn.classList.add('text-slate-400', 'hover:text-slate-200');
      });
      const activeBtn = document.getElementById(`tab-btn-${tabName}`);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-400', 'hover:text-slate-200');
        activeBtn.classList.add('bg-gradient-to-r', 'from-tactical-accent', 'to-orange-600', 'text-white', 'shadow-md', 'font-bold');
      }

      const calView = document.getElementById('view-calendar');
      const mapView = document.getElementById('view-map-container');

      if (tabName === 'calendar') {
        calView.classList.remove('hidden');
        mapView.classList.add('hidden');
      } else {
        calView.classList.add('hidden');
        mapView.classList.remove('hidden');
        
        // Configurar sidebar según pestaña
        if (tabName === 'monitor') {
          setSidebarTab('clusters');
        } else if (tabName === 'tactical') {
          setSidebarTab('escape');
        }
        
        setTimeout(() => { if (map) map.invalidateSize(); }, 60);
      }
    }

    // Manejo de Sidebar Táctico
    function toggleSidebar() {
      AppState.sidebarOpen = !AppState.sidebarOpen;
      const sb = document.getElementById('mission-sidebar');
      const icon = document.getElementById('sidebar-toggle-icon');
      if (AppState.sidebarOpen) {
        sb.classList.remove('-translate-x-[115%]');
        icon.innerText = '◀';
      } else {
        sb.classList.add('-translate-x-[115%]');
        icon.innerText = '▶';
      }
    }

    function setSidebarTab(tabKey) {
      AppState.sidebarTab = tabKey;
      const tabs = ['clusters', 'inspector', 'weather', 'escape'];
      tabs.forEach(t => {
        const btn = document.getElementById(`sb-tab-${t}`);
        const pane = document.getElementById(`sb-content-${t}`);
        if (t === tabKey) {
          btn.className = "flex-1 py-1.5 px-2 rounded-lg transition-all text-center bg-tactical-accent text-white font-bold";
          pane.classList.remove('hidden');
        } else {
          btn.className = "flex-1 py-1.5 px-2 rounded-lg transition-all text-center text-slate-400 hover:text-white";
          pane.classList.add('hidden');
        }
      });
      
      // Asegurarse de que el sidebar esté abierto
      if (!AppState.sidebarOpen) toggleSidebar();
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

      for (let m = 0; m < 12; m++) {
        const monthWeeks = weeks.filter(w => Math.min(11, Math.floor((w.week - 1) / 4.33)) === m);
        const col = document.createElement('div');
        col.className = "glass-inset p-2 rounded-xl border border-tactical-800 flex flex-col space-y-1.5";
        
        const title = document.createElement('div');
        title.className = "text-[10px] font-mono font-bold text-slate-400 text-center border-b border-tactical-800/80 pb-1";
        title.innerText = monthNames[m];
        col.appendChild(title);

        monthWeeks.forEach(w => {
          const cell = document.createElement('button');
          const isCurr = w.is_current;
          cell.className = `w-full py-1.5 px-1 rounded text-[9px] font-mono flex items-center justify-between border transition-all ${
            isCurr ? 'current-week-pulse border-tactical-accent font-black shadow-lg shadow-tactical-accent/40' : 'border-slate-800/60 hover:scale-105'
          }`;
          cell.style.backgroundColor = w.color;
          cell.style.color = (w.tier >= 1) ? '#000000' : '#64748B';
          cell.innerHTML = `<span>S${w.week}</span><span>${w.observed_raw > 0 ? (w.observed_raw + '🔥') : '·'}</span>`;
          cell.onclick = () => showWeekDetail(w);
          col.appendChild(cell);
        });

        grid.appendChild(col);
      }

      const currentWeekObj = weeks.find(w => w.is_current) || weeks[0];
      if (currentWeekObj) showWeekDetail(currentWeekObj);

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
        `Línea base histórica: ${w.baseline_mean} ± ${w.baseline_std} focos. Desvío: ${w.z_score >= 0 ? '+' : ''}${w.z_score}σ sobre la media climatológica.`;
    }

    // Gráfico SVG de la curva estacional interactiva
    function renderSeasonalSvgChart(weeks) {
      const svg = document.getElementById('cal-seasonal-chart');
      if (!svg || !weeks.length) return;

      const maxVal = Math.max(...weeks.map(w => w.baseline_mean + w.baseline_std)) * 1.25 || 250;
      const width = 800;
      const height = 240;
      const padLeft = 45;
      const padBottom = 25;
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
          currentBars.push(`<circle cx="${x}" cy="${yObs}" r="5.5" fill="#FF4D2D" stroke="#FFFFFF" stroke-width="2"><title>Semana ${w.week}: ${w.observed_harmonized} eq</title></circle>`);
        }
      });

      const bandPolygon = upperPoints.concat(lowerPoints).join(' ');
      const meanPolyline = meanPoints.join(' ');

      svg.innerHTML = `
        <defs>
          <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#06B6D4" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="#0284C7" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <line x1="${padLeft}" y1="20" x2="${width - 20}" y2="20" stroke="#162038" stroke-dasharray="4,4"/>
        <line x1="${padLeft}" y1="${20 + plotH / 2}" x2="${width - 20}" y2="${20 + plotH / 2}" stroke="#162038" stroke-dasharray="4,4"/>
        <line x1="${padLeft}" y1="${20 + plotH}" x2="${width - 20}" y2="${20 + plotH}" stroke="#233256"/>
        
        <polygon points="${bandPolygon}" fill="url(#bandGrad)" />
        <polyline points="${meanPolyline}" fill="none" stroke="#06B6D4" stroke-width="2.5"/>
        ${currentBars.join('')}
        
        <text x="50" y="${height - 6}" fill="#94A3B8" font-size="10" font-family="'JetBrains Mono', monospace">Ene</text>
        <text x="175" y="${height - 6}" fill="#94A3B8" font-size="10" font-family="'JetBrains Mono', monospace">Abr</text>
        <text x="360" y="${height - 6}" fill="#94A3B8" font-size="10" font-family="'JetBrains Mono', monospace">Jul</text>
        <text x="530" y="${height - 6}" fill="#F59E0B" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="bold">Oct (Pico)</text>
        <text x="730" y="${height - 6}" fill="#94A3B8" font-size="10" font-family="'JetBrains Mono', monospace">Dic</text>
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
      AppState.layers.safeZones = L.featureGroup().addTo(map);
      AppState.layers.escapeRoute = L.featureGroup().addTo(map);

      // Custom Layer Control
      L.control.layers({
        "🛰️ Satélite Esri": satLayer,
        "🗺️ Callejero OSM": osmLayer
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

      // Actualizar contador en sidebar
      const badgeCount = document.getElementById('badge-clusters-count');
      if (badgeCount) badgeCount.innerText = `${events.length} frentes`;

      // Rellenar lista de frentes en Sidebar
      const sbClusterList = document.getElementById('sidebar-cluster-list');
      sbClusterList.innerHTML = '';
      events.forEach(ev => {
        const item = document.createElement('div');
        item.className = "p-3 rounded-xl glass-inset hover:bg-tactical-850/80 border border-tactical-800 transition-all cursor-pointer space-y-2";
        const locLabel = ev.location_name || 'Sierras de Córdoba / San Luis';
        const frpVal = Math.round(ev.frp_peak_mw || ev.frp_total_mw);
        
        item.innerHTML = `
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-white font-mono">${ev.event_id}</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full ${ev.severity_level === 'CRÍTICA' ? 'bg-red-950 text-red-400 border border-red-700/60' : 'bg-amber-950 text-amber-400 border border-amber-700/60'} font-mono font-bold">
              ${ev.severity_level || 'ALTO'}
            </span>
          </div>
          <div class="text-[10px] text-slate-300 font-mono truncate">${locLabel}</div>
          <div class="grid grid-cols-3 gap-1 pt-1 border-t border-tactical-800/60 text-[10px] font-mono">
            <div><span class="text-slate-500">ÁREA</span><div class="font-bold text-slate-200 font-mono-numbers">${ev.detection_area_ha} ha</div></div>
            <div><span class="text-slate-500">VELOCIDAD</span><div class="font-bold text-amber-400 font-mono-numbers">${ev.spread_speed_kmh} km/h</div></div>
            <div><span class="text-slate-500">FRP PICO</span><div class="font-bold text-tactical-accent font-mono-numbers">${frpVal} MW</div></div>
          </div>
        `;
        item.onclick = () => {
          AppState.selectedCluster = ev;
          updateClusterDisplay();
          recalculatePredictiveEngine();
          map.setView([ev.centroid_lat, ev.centroid_lon], 13);
        };
        sbClusterList.appendChild(item);
      });

      // Poblar puntos VIIRS y MODIS
      AppState.layers.viirsPoints.clearLayers();
      AppState.layers.modisPoints.clearLayers();
      if (Array.isArray(data.points)) {
        data.points.forEach(pt => {
          const isViirs = pt.sensor_family === 'VIIRS';
          const popupHtml = `
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; min-width: 200px;">
              <b style="color: ${isViirs ? '#F59E0B' : '#EF4444'};">${isViirs ? '🟠 VIIRS 375m' : '🔴 MODIS 1km'} (${pt.satellite_name})</b><br>
              <hr style="margin: 4px 0; border-color: rgba(255,255,255,0.15);">
              <b>FRP:</b> ${pt.frp_mw} MW (${pt.frp_density_mw_km2} MW/km²)<br>
              <b>Temp. Brillo (4µm):</b> ${pt.temp_ch4_k} K<br>
              <b>Anomalía ΔT:</b> ${pt.delta_temp_k} K<br>
              <b>Huella Píxel:</b> ${pt.pixel_area_km2} km²<br>
              <b>Confianza:</b> ${pt.confidence_cat}<br>
              <b>UTC:</b> ${pt.acq_datetime}
            </div>
          `;
          
          let marker;
          if (isViirs) {
            marker = L.circleMarker([pt.latitude, pt.longitude], {
              radius: 5,
              color: '#D97706',
              fillColor: '#F59E0B',
              fillOpacity: 0.9,
              weight: 1.5
            }).bindPopup(popupHtml).addTo(AppState.layers.viirsPoints);
          } else {
            marker = L.circleMarker([pt.latitude, pt.longitude], {
              radius: 9,
              color: '#991B1B',
              fillColor: '#EF4444',
              fillOpacity: 0.75,
              weight: 2
            }).bindPopup(popupHtml).addTo(AppState.layers.modisPoints);
          }

          marker.on('click', () => {
            inspectHotspot(pt);
          });
        });
      }

      updateClusterDisplay();
    }

    function inspectHotspot(pt) {
      AppState.selectedHotspot = pt;
      const isViirs = pt.sensor_family === 'VIIRS';
      
      const elFamily = document.getElementById('insp-sensor-family');
      elFamily.className = `px-2 py-0.5 rounded ${isViirs ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'} text-[10px] font-bold`;
      elFamily.innerText = `${pt.sensor_family} (${isViirs ? '375m' : '1000m'})`;

      document.getElementById('insp-satellite').innerText = pt.satellite_name;
      document.getElementById('insp-frp').innerText = `${pt.frp_mw} MW`;
      document.getElementById('insp-frp-density').innerText = `${pt.frp_density_mw_km2} MW/km²`;
      document.getElementById('insp-temp-ch4').innerText = `${pt.temp_ch4_k} K`;
      document.getElementById('insp-delta-t').innerText = `${pt.delta_temp_k} K`;
      document.getElementById('insp-confidence').innerText = pt.confidence_cat || 'Alta';

      setSidebarTab('inspector');
    }

    function updateClusterDisplay() {
      if (!AppState.selectedCluster) return;
      const c = AppState.selectedCluster;
      document.getElementById('brigade-selected-cluster').innerText = c.event_id;
      document.getElementById('brigade-area').innerText = `${c.detection_area_ha} ha`;
      document.getElementById('brigade-sat-speed').innerText = `${c.spread_speed_kmh} km/h`;
      document.getElementById('hud-frp').innerText = `${c.frp_peak_mw || c.frp_total_mw} MW`;
    }

    // Timeline Scrubber Initialization
    function initTimelineScrubber() {
      const data = AppState.dashboardData;
      if (!data || !data.temporal_series) return;
      const series = data.temporal_series;
      const slider = document.getElementById('timeline-slider');
      slider.max = series.length;
      slider.value = series.length;
      AppState.timelineCurrentIndex = series.length;
      updateTimelineView(series.length);
    }

    function onTimelineSliderChange(val) {
      AppState.timelineCurrentIndex = parseInt(val);
      updateTimelineView(AppState.timelineCurrentIndex);
    }

    function updateTimelineView(index) {
      const series = AppState.dashboardData.temporal_series || [];
      const badge = document.getElementById('timeline-step-badge');
      const label = document.getElementById('timeline-pass-label');

      if (index >= series.length) {
        badge.innerText = `${series.length}/${series.length}`;
        label.innerText = "Todas las Pasadas (NRT)";
        if (AppState.layers.viirsPoints) AppState.layers.viirsPoints.setStyle({ opacity: 1, fillOpacity: 0.9 });
        if (AppState.layers.modisPoints) AppState.layers.modisPoints.setStyle({ opacity: 1, fillOpacity: 0.75 });
      } else {
        const pass = series[index];
        badge.innerText = `${index + 1}/${series.length}`;
        label.innerText = `${pass.timestamp_hour_utc} (${pass.sensor_family})`;
      }
    }

    function toggleTimelinePlay() {
      AppState.timelinePlaying = !AppState.timelinePlaying;
      const btn = document.getElementById('btn-timeline-play');
      const icon = document.getElementById('play-icon');

      if (AppState.timelinePlaying) {
        icon.innerText = '⏸';
        btn.classList.add('bg-emerald-600');
        const series = AppState.dashboardData.temporal_series || [];
        AppState.timelineTimer = setInterval(() => {
          let curr = parseInt(document.getElementById('timeline-slider').value);
          curr = (curr + 1) > series.length ? 0 : curr + 1;
          document.getElementById('timeline-slider').value = curr;
          onTimelineSliderChange(curr);
        }, 1200);
      } else {
        icon.innerText = '▶';
        btn.classList.remove('bg-emerald-600');
        if (AppState.timelineTimer) clearInterval(AppState.timelineTimer);
      }
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

      document.getElementById('weather-wind-speed').innerText = `${Math.round(w.windSpeedKmh)} km/h`;
      document.getElementById('weather-wind-dir').innerText = `${Math.round(w.windDirectionDeg)}° (${degreesToCardinal(w.windDirectionDeg)})`;
      document.getElementById('weather-temp').innerText = `${Math.round(w.temperatureC)} °C`;
      document.getElementById('weather-humidity').innerText = `${Math.round(w.relativeHumidity)} %`;

      const pushAzimuth = (w.windDirectionDeg + 180) % 360;
      document.getElementById('hud-wind-arrow').style.transform = `rotate(${pushAzimuth}deg)`;

      const compassArrow = document.getElementById('floating-compass-arrow');
      if (compassArrow) compassArrow.style.transform = `rotate(${w.windDirectionDeg}deg)`;
      const compassCardinal = document.getElementById('floating-wind-cardinal');
      if (compassCardinal) compassCardinal.innerText = degreesToCardinal(w.windDirectionDeg);

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
        }).bindPopup(`
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">
            <b style="color: #EF4444;">🔥 ${ev.event_id}</b><br>
            <b>Zona:</b> ${ev.location_name || 'Sierras'}<br>
            <b>Severidad:</b> ${ev.severity_level}<br>
            <b>Área:</b> ${ev.detection_area_ha} ha<br>
            <b>FRP Pico:</b> ${ev.frp_peak_mw} MW
          </div>
        `).addTo(AppState.layers.firePolygons);

        // Conos Predictivos con Turf.js
        const satSpeed = ev.spread_speed_kmh || 0.0;
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
        banner.className = "bg-gradient-to-r from-red-600 via-rose-600 to-red-700 text-white px-4 py-2 border-b border-red-500/50 flex items-center justify-between shrink-0 shadow-xl animate-pulse z-30";
        title.innerText = "🚨 ALERTA ROJA: IMPACTO INMINENTE";
        desc.innerText = `Fuego avanzando a ${cluster.projSpeedKmh.toFixed(1)} km/h hacia su posición. Evacúe de inmediato por la ruta marcada.`;
        etaDisplay.innerText = etaMinutes + " MIN";
        triggerBeepAlert();
      } else if (distToFireKm < 10.0) {
        banner.className = "bg-gradient-to-r from-amber-600 to-orange-600 text-white px-4 py-2 border-b border-amber-500/50 flex items-center justify-between shrink-0 shadow-xl z-30";
        title.innerText = "⚠️ PRE-ALERTA: FUEGO EN LA ZONA";
        desc.innerText = `Frente activo a ${distToFireKm.toFixed(1)} km. Monitoree rotación de viento y prepare salida.`;
        etaDisplay.innerText = isHeadingToUser ? (etaMinutes + " MIN") : "FUERA DE EJE";
      } else {
        banner.className = "bg-gradient-to-r from-emerald-700 to-teal-800 text-white px-4 py-2 border-b border-emerald-600/50 flex items-center justify-between shrink-0 shadow-xl z-30";
        title.innerText = "🛡️ ZONA EN VIGILANCIA";
        desc.innerText = "Sin frentes activos en trayectoria de impacto directo.";
        etaDisplay.innerText = "> 3 HORAS";
      }

      // Safe Zone a Barlovento (Upwind)
      const escapeAzimuth = AppState.weather.windDirectionDeg;
      const safePt = turf.transformTranslate(uPt, 2.5, escapeAzimuth);
      const safeCoords = safePt.geometry.coordinates;

      AppState.currentSafeZoneTarget = { lat: safeCoords[1], lon: safeCoords[0] };

      L.circleMarker([safeCoords[1], safeCoords[0]], {
        radius: 10,
        color: '#10B981',
        fillColor: '#059669',
        fillOpacity: 0.9,
        weight: 3
      }).bindPopup(`
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">
          <b style="color: #10B981;">🛡️ ZONA SEGURA RECOMENDADA</b><br>
          Posición a barlovento libre de avance y columnas convectivas de humo.
        </div>
      `).addTo(AppState.layers.safeZones);

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
        bBrigade.className = "flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 font-bold shadow-md";
        bUser.className = "flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200";
        pBrigade.classList.remove('hidden');
        pUser.classList.add('hidden');
      } else {
        bUser.className = "flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 bg-gradient-to-r from-tactical-accent to-red-600 text-white font-bold shadow-md";
        bBrigade.className = "flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 text-slate-400 hover:text-slate-200";
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

    // Sintetizador de Alerta Sonora con Web Audio API
    function toggleTacticalAudio() {
      AppState.audioEnabled = !AppState.audioEnabled;
      const icon = document.getElementById('audio-icon');
      icon.innerText = AppState.audioEnabled ? '🔊' : '🔇';
    }

    function triggerBeepAlert() {
      if (!AppState.audioEnabled) return;
      try {
        if (!AppState.audioCtx) {
          AppState.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (AppState.audioCtx.state === 'suspended') {
          AppState.audioCtx.resume();
        }
        const osc = AppState.audioCtx.createOscillator();
        const gain = AppState.audioCtx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(880, AppState.audioCtx.currentTime); // A5
        osc.frequency.exponentialRampToValueAtTime(440, AppState.audioCtx.currentTime + 0.3);
        gain.gain.setValueAtTime(0.12, AppState.audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.01, AppState.audioCtx.currentTime + 0.3);
        osc.connect(gain);
        gain.connect(AppState.audioCtx.destination);
        osc.start();
        osc.stop(AppState.audioCtx.currentTime + 0.3);
      } catch (e) {}
    }

    // Modal SOS
    function openSosModal() {
      const lat = AppState.userLocation.lat;
      const lon = AppState.userLocation.lon;
      const latStr = lat.toFixed(5);
      const lonStr = lon.toFixed(5);

      document.getElementById('sos-gps-text').innerText = `${latStr}, ${lonStr}`;
      document.getElementById('sos-dms-text').innerText = `${toDMS(lat, true)}, ${toDMS(lon, false)}`;
      document.getElementById('sos-eta-text').innerText = document.getElementById('fsm-eta-display').innerText;
      document.getElementById('sos-wind-text').innerText = `${Math.round(AppState.weather.windSpeedKmh)} km/h hacia el ${degreesToCardinal((AppState.weather.windDirectionDeg + 180) % 360)}`;
      
      const mapsUrl = `https://maps.google.com/?q=${latStr},${lonStr}`;
      const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(mapsUrl)}`;
      document.getElementById('sos-qr-image').src = qrUrl;

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

    function openMissionModal() {
      document.getElementById('modal-mission').classList.remove('hidden');
    }

    function closeMissionModal() {
      document.getElementById('modal-mission').classList.add('hidden');
    }

    function degreesToCardinal(deg) {
      const c = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
      return c[Math.round(deg / 45) % 8];
    }

    function toDMS(coord, isLat) {
      const dir = isLat ? (coord >= 0 ? 'N' : 'S') : (coord >= 0 ? 'E' : 'W');
      const absVal = Math.abs(coord);
      const deg = Math.floor(absVal);
      const min = Math.floor((absVal - deg) * 60);
      const sec = ((absVal - deg - min / 60) * 3600).toFixed(1);
      return `${deg}° ${min}' ${sec}" ${dir}`;
    }
  </script>
</body>
</html>
'''

def main():
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    html_content = get_template()
    
    tactical_path = os.path.join(output_dir, "app_tactica_mobile.html")
    with open(tactical_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"🚀 Portal Unificado AURA-FIRE generado con éxito:")
    print(f"   - {tactical_path} ({os.path.getsize(tactical_path)} bytes)")
    print(f"   - {index_path} ({os.path.getsize(index_path)} bytes)")

if __name__ == "__main__":
    main()
