#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
NASA Space Apps Challenge - MODIS & VIIRS Hot Spots Analytics Pipeline
=============================================================================
Módulo principal para ingesta, armonización científica, clustering geodésico
(DBSCAN), cinemática de frentes de fuego y visualización interactiva de
anomalías térmicas satelitales (NASA FIRMS).

Autor: Equipo NASA Space Apps
Licencia: MIT / Open Science
=============================================================================
"""

import os
import sys
import io
import time
import math
import json
import argparse
from datetime import datetime
from typing import Tuple, Dict, Any, List, Optional

import numpy as np
import pandas as pd
import requests

from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull

# Opcionales para visualización
try:
    import folium
    from folium.plugins import HeatMap, MeasureControl, Fullscreen
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False


# =============================================================================
# CONSTANTES Y CONFIGURACIÓN PREDETERMINADA
# =============================================================================
DEFAULT_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "35607fe3f0cf2c7a2a3e5a45fc011873")
DEFAULT_ARGENTINA_BBOX = "-66.0,-33.5,-63.5,-31.0"


# =============================================================================
# BLOQUE 1: INGESTA DE DATOS CON CACHÉ Y TOLERANCIA A FALLOS
# =============================================================================

class FIRMSDataIngestor:
    """
    Gestiona la descarga y almacenamiento en caché de datos de NASA FIRMS.
    Soporta MODIS_NRT, VIIRS_NOAA20_NRT y VIIRS_SNPP_NRT.
    """

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def __init__(self, map_key: str, cache_dir: str = "data/raw"):
        self.map_key = map_key
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_source(self, source: str, area: str, day_range: int, date: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Descarga o carga desde caché un sensor específico.
        area: 'min_lon,min_lat,max_lon,max_lat'
        date: fecha opcional en formato YYYY-MM-DD para consultas históricas
        """
        clean_area = area.replace(",", "_")
        date_suffix = f"_{date}" if date else ""
        cache_file = os.path.join(self.cache_dir, f"{source}_{clean_area}{date_suffix}_{day_range}d.csv")

        if use_cache and os.path.exists(cache_file):
            print(f"📦 [Caché] Cargando {source} desde {cache_file}...")
            try:
                df = pd.read_csv(cache_file)
                df["sensor_source"] = source
                df["is_synthetic"] = False
                return df
            except Exception as e:
                print(f"⚠️ Error leyendo caché ({e}). Reintentando descarga...")

        if date:
            url = f"{self.BASE_URL}/{self.map_key}/{source}/{area}/{day_range}/{date}"
            print(f"🌐 [NASA FIRMS API] Consultando {source} para área [{area}] ({day_range} días desde {date})...")
        else:
            url = f"{self.BASE_URL}/{self.map_key}/{source}/{area}/{day_range}"
            print(f"🌐 [NASA FIRMS API] Consultando {source} para área [{area}] ({day_range} días)...")

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200 and len(response.text.strip()) > 0:
                if "No fires detected" in response.text or "Invalid MAP_KEY" in response.text:
                    print(f"⚠️ Respuesta API {source}: {response.text.strip()[:100]}")
                    return pd.DataFrame()

                df = pd.read_csv(io.StringIO(response.text))
                df["sensor_source"] = source
                df["is_synthetic"] = False
                # Guardar en caché
                df.to_csv(cache_file, index=False)
                print(f"✅ {source}: {len(df)} registros descargados y guardados en caché.")
                return df
            else:
                print(f"❌ Error HTTP {response.status_code} al consultar {source}: {response.text[:120]}")
        except Exception as err:
            print(f"❌ Excepción de red al conectar con NASA FIRMS ({source}): {err}")

        return pd.DataFrame()

    def fetch_all(self, area: str, day_range: int = 5,
                  date: Optional[str] = None,
                  sources: Optional[List[str]] = None,
                  use_cache: bool = True) -> pd.DataFrame:
        """
        Descarga y consolida todas las fuentes satelitales configuradas.
        No inyecta datos falsos: si no hay detecciones, retorna DataFrame vacío.
        """
        if sources is None:
            sources = ["VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT", "MODIS_NRT"]

        dfs = []
        for src in sources:
            df_src = self.fetch_source(src, area, day_range, date=date, use_cache=use_cache)
            if not df_src.empty:
                dfs.append(df_src)
            # Respetar rate limit de FIRMS API
            time.sleep(1.0)

        if not dfs:
            print("ℹ️ [NASA FIRMS] No se obtuvieron registros satelitales para los parámetros indicados.")
            return pd.DataFrame()

        df_raw = pd.concat(dfs, ignore_index=True)
        df_raw["is_synthetic"] = False
        print(f"\n📊 Total registros crudos recopilados: {len(df_raw)}")
        return df_raw

    def generate_calibrated_fallback(self, area: str) -> pd.DataFrame:
        """
        Genera un dataset sintético científicamente calibrado (MODIS + VIIRS)
        con frentes de fuego activos en caso de no disponer de conexión o API key válida.
        """
        print("💡 Generando conjunto de datos científico de respaldo para demostración...")
        try:
            lons = [float(x) for x in area.split(",")]
            min_lon, min_lat, max_lon, max_lat = lons[0], lons[1], lons[2], lons[3]
        except Exception:
            min_lon, min_lat, max_lon, max_lat = -121.0, 37.0, -119.0, 39.0

        np.random.seed(42)
        n_clusters = 4
        records = []

        # Centros de fuego
        centers = [
            (min_lat + 0.3 * (max_lat - min_lat), min_lon + 0.4 * (max_lon - min_lon)),
            (min_lat + 0.7 * (max_lat - min_lat), min_lon + 0.6 * (max_lon - min_lon)),
            (min_lat + 0.5 * (max_lat - min_lat), min_lon + 0.2 * (max_lon - min_lon)),
            (min_lat + 0.8 * (max_lat - min_lat), min_lon + 0.8 * (max_lon - min_lon)),
        ]

        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        for c_idx, (clat, clon) in enumerate(centers):
            # VIIRS detections (alta resolución, píxeles pequeños)
            n_viirs = np.random.randint(25, 60)
            for i in range(n_viirs):
                dlat = np.random.normal(0, 0.015)
                dlon = np.random.normal(0, 0.015) + (i * 0.0003)  # avance
                t4 = np.random.uniform(325.0, 480.0)
                t5 = t4 - np.random.uniform(15.0, 60.0)
                frp = np.random.exponential(18.0) + 1.5
                conf = np.random.choice(["h", "n", "l"], p=[0.7, 0.25, 0.05])
                records.append({
                    "latitude": clat + dlat,
                    "longitude": clon + dlon,
                    "bright_ti4": round(t4, 2),
                    "scan": 0.38,
                    "track": 0.37,
                    "acq_date": today_str,
                    "acq_time": f"{np.random.randint(10, 22):02d}{np.random.randint(0, 59):02d}",
                    "satellite": "NOAA-20",
                    "confidence": conf,
                    "version": "2.0NRT",
                    "bright_ti5": round(t5, 2),
                    "frp": round(frp, 2),
                    "daynight": "D",
                    "sensor_source": "VIIRS_NOAA20_NRT"
                })

            # MODIS detections (resolución 1km, detecta focos mayores)
            n_modis = max(2, n_viirs // 6)
            for _ in range(n_modis):
                dlat = np.random.normal(0, 0.02)
                dlon = np.random.normal(0, 0.02)
                t_modis = np.random.uniform(315.0, 410.0)
                t31 = t_modis - np.random.uniform(10.0, 45.0)
                frp = np.random.exponential(35.0) + 5.0
                conf = int(np.random.uniform(50, 100))
                records.append({
                    "latitude": clat + dlat,
                    "longitude": clon + dlon,
                    "brightness": round(t_modis, 2),
                    "scan": 1.1,
                    "track": 1.0,
                    "acq_date": today_str,
                    "acq_time": f"{np.random.randint(10, 22):02d}{np.random.randint(0, 59):02d}",
                    "satellite": "Aqua",
                    "confidence": conf,
                    "version": "6.1NRT",
                    "bright_t31": round(t31, 2),
                    "frp": round(frp, 2),
                    "daynight": "D",
                    "sensor_source": "MODIS_NRT"
                })

        df_fallback = pd.DataFrame(records)
        df_fallback["is_synthetic"] = True
        print(f"✅ Dataset de respaldo generado con {len(df_fallback)} detecciones.")
        return df_fallback


# =============================================================================
# BLOQUE 2: ARMONIZACIÓN CIENTÍFICA Y NORMALIZACIÓN FÍSICA
# =============================================================================

class ModisViirsHarmonizer:
    """
    Normaliza y unifica física y estadísticamente las detecciones MODIS y VIIRS:
    1. Unifica canales térmicos ~4um y ~11um
    2. Calcula diferencial térmico (anomalía     de fuego)
    3. Normaliza escalas de confianza (0-100 vs l/n/h -> categoría + score 0-1)
    4. Computa área del píxel proyectado y densidad de FRP (MW/km²)
    5. Normaliza marcas temporales en datetime UTC
    """

    @staticmethod
    def _map_confidence_row(val: Any) -> Tuple[str, float]:
        if pd.isna(val):
            return "Nominal", 0.50

        s_val = str(val).strip().lower()

        # VIIRS categorical mapping
        if s_val in ["h", "high"]:
            return "High", 0.95
        if s_val in ["n", "nominal"]:
            return "Nominal", 0.65
        if s_val in ["l", "low"]:
            return "Low", 0.30

        # MODIS numeric percentage mapping (0 - 100)
        try:
            num = float(s_val)
            score = max(0.0, min(1.0, num / 100.0))
            if num >= 80.0:
                return "High", score
            elif num >= 30.0:
                return "Nominal", score
            else:
                return "Low", score
        except ValueError:
            return "Nominal", 0.50

    def harmonize(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Ejecuta la armonización completa sobre el DataFrame crudo.
        """
        if df_raw.empty:
            return pd.DataFrame()

        df = df_raw.copy()

        # 1. Identificar familia de sensor y decodificar nombre de satélite
        if "sensor_family" not in df.columns:
            def identify_sensor(row):
                inst = str(row.get("instrument", "")).upper()
                src = str(row.get("sensor_source", "")).upper()
                sat = str(row.get("satellite", "")).upper()
                if "VIIRS" in inst or "VIIRS" in src or sat in ["N", "N20", "N21", "J1", "J2", "NOAA-20", "NOAA-21", "SNPP"]:
                    return "VIIRS"
                elif "MODIS" in inst or "MODIS" in src or "TERRA" in sat or "AQUA" in sat or sat in ["T", "A"]:
                    return "MODIS"
                elif "bright_ti4" in row and pd.notna(row["bright_ti4"]):
                    return "VIIRS"
                else:
                    return "MODIS"

            df["sensor_family"] = df.apply(identify_sensor, axis=1)

        sat_map = {
            "N20": "NOAA-20", "1": "NOAA-20", "J1": "NOAA-20", "NOAA-20": "NOAA-20",
            "N21": "NOAA-21", "2": "NOAA-21", "J2": "NOAA-21", "NOAA-21": "NOAA-21",
            "N": "Suomi-NPP", "SNPP": "Suomi-NPP", "SUOMI-NPP": "Suomi-NPP",
            "TERRA": "Terra", "T": "Terra",
            "AQUA": "Aqua", "A": "Aqua"
        }
        if "satellite" in df.columns:
            df["satellite_name"] = df["satellite"].astype(str).str.strip().str.upper().map(
                lambda x: sat_map.get(x, x)
            )
        else:
            df["satellite_name"] = df["sensor_family"]

        # 2. Armonizar Canal Térmico 4 (~4 µm, detección de combustión)
        # VIIRS usa 'bright_ti4', MODIS usa 'brightness'
        col_t4_viirs = df["bright_ti4"] if "bright_ti4" in df.columns else pd.Series(np.nan, index=df.index)
        col_t4_modis = df["brightness"] if "brightness" in df.columns else pd.Series(np.nan, index=df.index)
        df["temp_ch4_k"] = col_t4_viirs.combine_first(col_t4_modis)

        # 3. Armonizar Canal Térmico 5 (~11 µm, fondo / nubes / humo)
        # VIIRS usa 'bright_ti5', MODIS usa 'bright_t31'
        col_t5_viirs = df["bright_ti5"] if "bright_ti5" in df.columns else pd.Series(np.nan, index=df.index)
        col_t5_modis = df["bright_t31"] if "bright_t31" in df.columns else pd.Series(np.nan, index=df.index)
        df["temp_ch5_k"] = col_t5_viirs.combine_first(col_t5_modis)

        # 4. Diferencial Térmico (Firma característica de combustión)
        df["delta_temp_k"] = (df["temp_ch4_k"] - df["temp_ch5_k"]).round(2)

        # 5. Huella espacial y Densidad de Potencia Radiativa
        # Si scan/track faltan, asignar valores nominales nadir (MODIS=1.0km, VIIRS=0.375km)
        scan = df["scan"] if "scan" in df.columns else pd.Series(np.nan, index=df.index)
        track = df["track"] if "track" in df.columns else pd.Series(np.nan, index=df.index)

        nominal_scan = df["sensor_family"].apply(lambda s: 0.375 if s == "VIIRS" else 1.0)
        nominal_track = df["sensor_family"].apply(lambda s: 0.375 if s == "VIIRS" else 1.0)

        df["scan_km"] = scan.fillna(nominal_scan).clip(lower=0.2, upper=5.0)
        df["track_km"] = track.fillna(nominal_track).clip(lower=0.2, upper=5.0)
        df["pixel_area_km2"] = (df["scan_km"] * df["track_km"]).round(4)

        # FRP (Fire Radiative Power)
        df["frp_mw"] = pd.to_numeric(df["frp"], errors="coerce").fillna(0.0).clip(lower=0.0)
        df["frp_density_mw_km2"] = (df["frp_mw"] / df["pixel_area_km2"].replace(0, np.nan)).fillna(0.0).round(2)

        # 6. Estandarización de Confianza
        conf_results = df["confidence"].apply(self._map_confidence_row)
        df["confidence_cat"] = [r[0] for r in conf_results]
        df["confidence_score"] = [r[1] for r in conf_results]

        # 7. Factor de Equivalencia y Calibración Inter-Sensor (MODIS <-> VIIRS)
        # Fundamento físico: VIIRS (375m, huella 0.14 km²) detecta ~4.0x más focos que MODIS (1km, huella 1.0 km²)
        # Para reconstruir series continuas históricas pre-2012 y armonizar conteos, se calcula el conteo equivalente
        def compute_viirs_equiv(row):
            if row["sensor_family"] == "VIIRS":
                return 1.0
            area = float(row.get("pixel_area_km2", 1.0))
            ratio = 4.0 * math.sqrt(max(0.5, min(area, 6.0)))
            return round(ratio, 2)

        df["viirs_equiv_count"] = df.apply(compute_viirs_equiv, axis=1)
        df["frp_harmonized_mw"] = np.where(
            df["sensor_family"] == "MODIS",
            (df["frp_mw"] * 0.92).round(2),
            df["frp_mw"].round(2)
        )

        # 8. Formato Temporal Estandarizado (UTC Datetime)
        def parse_datetime(row):
            d_str = str(row.get("acq_date", "")).strip()
            t_str = str(row.get("acq_time", "")).strip()
            t_str = t_str.split(".")[0].zfill(4)
            try:
                return datetime.strptime(f"{d_str} {t_str}", "%Y-%m-%d %H%M")
            except Exception:
                return pd.NaT

        df["acq_datetime"] = df.apply(parse_datetime, axis=1)

        # 8. Flag de origen de datos (real vs sintético)
        if "is_synthetic" not in df.columns:
            df["is_synthetic"] = False

        # 9. Filtro de consistencia física
        # Temperaturas válidas de brillo terrestre: 270 K a 550 K
        valid_mask = (
            df["latitude"].notna() &
            df["longitude"].notna() &
            df["temp_ch4_k"].notna() &
            (df["temp_ch4_k"] >= 270.0) &
            (df["temp_ch4_k"] <= 550.0) &
            (df["latitude"].between(-90, 90)) &
            (df["longitude"].between(-180, 180))
        )
        df_clean = df[valid_mask].copy()

        # Selección de columnas ordenadas para análisis
        cols_priority = [
            "latitude", "longitude", "sensor_family", "satellite",
            "temp_ch4_k", "temp_ch5_k", "delta_temp_k",
            "frp_mw", "frp_harmonized_mw", "pixel_area_km2", "frp_density_mw_km2",
            "viirs_equiv_count",
            "confidence_cat", "confidence_score",
            "acq_datetime", "daynight", "scan_km", "track_km",
            "is_synthetic"
        ]
        remaining = [c for c in df_clean.columns if c not in cols_priority]
        df_clean = df_clean[cols_priority + remaining]

        print(f"✨ Armonización completada: {len(df_clean)} registros válidos listos para análisis.")
        print(f"   - VIIRS: {len(df_clean[df_clean['sensor_family'] == 'VIIRS'])} detecciones")
        print(f"   - MODIS: {len(df_clean[df_clean['sensor_family'] == 'MODIS'])} detecciones")
        return df_clean

    @staticmethod
    def compute_cross_sensor_calibration(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula métricas de calibración cruzada e inter-sensor entre MODIS y VIIRS.
        Compara conteos crudos vs armonizados y detecta eventos colocalizados.
        """
        if df.empty or "sensor_family" not in df.columns:
            return {"status": "Sin datos para calibración"}

        viirs_df = df[df["sensor_family"] == "VIIRS"]
        modis_df = df[df["sensor_family"] == "MODIS"]

        total_v = len(viirs_df)
        total_m = len(modis_df)
        empirical_ratio = round(total_v / total_m, 2) if total_m > 0 else 4.0

        colocated_count = 0
        mean_delta_t4 = 0.0
        if total_v > 0 and total_m > 0 and "cluster_id" in df.columns:
            shared = set(viirs_df["cluster_id"]).intersection(set(modis_df["cluster_id"])) - {-1}
            colocated_count = len(shared)
            if colocated_count > 0:
                v_sub = viirs_df[viirs_df["cluster_id"].isin(shared)]
                m_sub = modis_df[modis_df["cluster_id"].isin(shared)]
                mean_delta_t4 = round(float(v_sub["temp_ch4_k"].mean() - m_sub["temp_ch4_k"].mean()), 2)

        return {
            "total_viirs_hotspots": total_v,
            "total_modis_hotspots": total_m,
            "empirical_count_ratio": empirical_ratio,
            "theoretical_nadir_footprint_ratio": 7.11,
            "effective_detection_ratio_literature": 4.0,
            "colocated_fronts_count": colocated_count,
            "mean_temp_ch4_difference_k": mean_delta_t4,
            "calibration_model": "Multi-Sensor Footprint Transfer & Harmonized Hotspot Count",
            "modis_equivalent_multiplier_applied": True
        }


# =============================================================================
# BLOQUE 3: CLUSTERING ESPACIOTEMPORAL Y CINEMÁTICA DE INCENDIOS
# =============================================================================

class FireEventClusterer:
    """
    Agrupa anomalías térmicas en Frentes de Incendio Activos usando DBSCAN
    con métrica geodésica (Haversine). Reconstruye la geometría,
    severidad y cinemática observada de cada incendio.
    """

    EARTH_RADIUS_KM = 6371.0088

    SIERRAS_LANDMARKS = [
        (-33.255, -65.953, "Sierras de San Luis (El Trapiche / La Florida)"),
        (-32.910, -65.428, "Valle del Conlara / El Morro (San Luis)"),
        (-32.117, -65.742, "Norte Puntano (Quines / Candelaria, San Luis)"),
        (-32.187, -65.659, "Sierra de las Quijadas / Luján (San Luis)"),
        (-32.052, -65.169, "Traslasierra Sur (San Javier / Yacanto, Córdoba)"),
        (-31.855, -65.551, "Reserva Chancaní / Oeste Traslasierra (Córdoba)"),
        (-31.725, -65.031, "Valle de Traslasierra (Mina Clavero / Cura Brochero, Córdoba)"),
        (-31.663, -63.833, "Pilar / Río Segundo (Córdoba)"),
        (-31.402, -64.117, "Sierras Chicas / Gran Córdoba (Córdoba)"),
        (-31.980, -64.560, "Valle de Calamuchita (Córdoba)"),
        (-31.150, -64.480, "Valle de Punilla (Córdoba)"),
    ]

    @classmethod
    def _resolve_local_toponym(cls, lat: float, lon: float) -> str:
        """Resuelve la localidad o zona serrana más cercana en Córdoba/San Luis."""
        best_name = "Región Serrana (Córdoba / San Luis)"
        best_dist = float("inf")
        for ref_lat, ref_lon, name in cls.SIERRAS_LANDMARKS:
            d_lat = (lat - ref_lat) * 111.32
            d_lon = (lon - ref_lon) * (111.32 * math.cos(math.radians(ref_lat)))
            dist_km = math.sqrt(d_lat ** 2 + d_lon ** 2)
            if dist_km < best_dist:
                best_dist = dist_km
                best_name = name
        if best_dist <= 65.0:
            return best_name
        return "Región Serrana (Córdoba / San Luis)"

    def __init__(self, eps_km: float = 2.5, min_samples: int = 2):
        self.eps_km = eps_km
        self.min_samples = min_samples

    def cluster_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ejecuta DBSCAN geodésico y asigna 'cluster_id' y 'event_type'.
        """
        if df.empty:
            return df

        df_res = df.copy()

        # Convertir coordenadas a radianes para Haversine
        coords_rad = np.radians(df_res[["latitude", "longitude"]].values)
        eps_rad = self.eps_km / self.EARTH_RADIUS_KM

        db = DBSCAN(eps=eps_rad, min_samples=self.min_samples, metric="haversine")
        df_res["cluster_id"] = db.fit_predict(coords_rad)

        # Distinguir focos aislados de frentes activos
        df_res["event_type"] = np.where(df_res["cluster_id"] >= 0, "Frente Activo", "Foco Aislado")

        n_clusters = len(set(df_res["cluster_id"])) - (1 if -1 in df_res["cluster_id"] else 0)
        n_isolated = (df_res["cluster_id"] == -1).sum()
        print(f"🛰️ Clustering DBSCAN (radio={self.eps_km} km): {n_clusters} frentes consolidados, {n_isolated} focos aislados.")

        return df_res

    def compute_event_metrics(self, df_clustered: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula estadísticas consolidadas por cada evento de incendio.
        """
        if df_clustered.empty:
            return pd.DataFrame()

        events = []

        # Procesar primero los clusters agrupados (cluster_id >= 0)
        grouped = df_clustered[df_clustered["cluster_id"] >= 0].groupby("cluster_id")

        for cid, grp in grouped:
            ev = self._process_cluster_group(cid, grp)
            events.append(ev)

        # Para los focos aislados (-1), generar un evento individual por cada uno
        isolated = df_clustered[df_clustered["cluster_id"] == -1]
        for idx, row in isolated.iterrows():
            cid = f"ISO_{row.name}"
            frp_val = round(float(row["frp_mw"]), 2)
            area_km2_val = round(float(row["pixel_area_km2"]), 4)
            area_ha_val = round(area_km2_val * 100.0, 2)
            temp_val = round(float(row["temp_ch4_k"]), 2)
            sat_name = str(row.get("satellite_name", row.get("satellite", "N/A")))
            iso_lat = round(float(row["latitude"]), 5)
            iso_lon = round(float(row["longitude"]), 5)
            iso_poly = self._generate_buffer_polygon(iso_lat, iso_lon, area_km2_val)
            ev = {
                "event_id": str(cid),
                "event_type": "Foco Aislado",
                "location_name": self._resolve_local_toponym(iso_lat, iso_lon),
                "cluster_numeric_id": -1,
                "centroid_lat": iso_lat,
                "centroid_lon": iso_lon,
                "points_count": 1,
                "viirs_count": 1 if row["sensor_family"] == "VIIRS" else 0,
                "modis_count": 1 if row["sensor_family"] == "MODIS" else 0,
                "multisensor_confirmed": False,
                "satellites_involved": sat_name,
                "frp_peak_mw": frp_val,
                "frp_total_mw": frp_val,
                "frp_max_mw": frp_val,
                "frp_mean_mw": frp_val,
                "frp_mean_density_mw_km2": round(float(row.get("frp_density_mw_km2", 0.0)), 2),
                "fre_est_mj": round(frp_val * 3600.0, 1),
                "temp_brightness_max_k": temp_val,
                "max_temp_k": temp_val,
                "mean_delta_temp_k": round(float(row["delta_temp_k"]), 2),
                "detection_area_km2": area_km2_val,
                "detection_area_ha": area_ha_val,
                "est_area_km2": area_km2_val,
                "est_area_ha": area_ha_val,
                "first_detected": row["acq_datetime"],
                "last_detected": row["acq_datetime"],
                "duration_hours": 0.0,
                "spread_vector_km": 0.0,
                "spread_speed_kmh": 0.0,
                "spread_azimuth_deg": None,
                "spread_cardinal": "Estacionario",
                "severity_level": self._classify_severity(frp_val),
                "polygon_coords": iso_poly
            }
            events.append(ev)

        df_events = pd.DataFrame(events)
        if not df_events.empty:
            df_events = df_events.sort_values(by="frp_peak_mw", ascending=False).reset_index(drop=True)

        return df_events

    def _process_cluster_group(self, cid: int, grp: pd.DataFrame) -> Dict[str, Any]:
        lats = grp["latitude"].values
        lons = grp["longitude"].values
        cent_lat = float(np.mean(lats))
        cent_lon = float(np.mean(lons))

        pts_count = len(grp)
        viirs_count = int((grp["sensor_family"] == "VIIRS").sum())
        modis_count = int((grp["sensor_family"] == "MODIS").sum())
        multisensor = (viirs_count > 0 and modis_count > 0)

        if "satellite_name" in grp.columns:
            sats = sorted(list(set(grp["satellite_name"].dropna().astype(str))))
        elif "satellite" in grp.columns:
            sats = sorted(list(set(grp["satellite"].dropna().astype(str))))
        else:
            sats = []
        satellites_involved = ", ".join(sats) if sats else "N/A"

        frp_tot = float(grp["frp_mw"].sum())
        frp_max = float(grp["frp_mw"].max())
        frp_mean = float(grp["frp_mw"].mean())
        frp_mean_density = float(grp["frp_density_mw_km2"].mean()) if "frp_density_mw_km2" in grp.columns else 0.0
        max_temp = float(grp["temp_ch4_k"].max())
        mean_delta = float(grp["delta_temp_k"].mean())

        # Potencia pico instantánea por pasada satelital y Energía Radiativa Estimada (FRE en MJ)
        valid_time_grp = grp.dropna(subset=["acq_datetime"])
        if not valid_time_grp.empty:
            pass_frp = valid_time_grp.groupby("acq_datetime")["frp_mw"].sum()
            frp_peak_pass = float(pass_frp.max())
            if len(pass_frp) >= 2:
                times_sorted = sorted(pass_frp.index)
                fre_mj = 0.0
                for idx_t in range(len(times_sorted) - 1):
                    t1, t2 = times_sorted[idx_t], times_sorted[idx_t + 1]
                    dt_sec = (t2 - t1).total_seconds()
                    if 0 < dt_sec <= 36 * 3600:
                        fre_mj += 0.5 * (float(pass_frp[t1]) + float(pass_frp[t2])) * dt_sec
                if fre_mj <= 0.0:
                    fre_mj = frp_peak_pass * 3600.0
            else:
                fre_mj = frp_peak_pass * 3600.0
        else:
            frp_peak_pass = frp_max
            fre_mj = frp_max * 3600.0

        # Estimación de superficie de envolvente de detección
        area_km2, poly_coords = self._calculate_convex_hull(lats, lons, cent_lat)
        if area_km2 <= 0.0:
            # Unión aproximada de huellas de píxeles
            area_km2 = float(grp["pixel_area_km2"].sum())

        if poly_coords is None:
            poly_coords = self._generate_buffer_polygon(cent_lat, cent_lon, area_km2)

        # Cinemática del avance
        spread_km, speed_kmh, azimuth, cardinal = self._compute_kinematics(grp, cent_lat, cent_lon)

        dt_min = grp["acq_datetime"].min()
        dt_max = grp["acq_datetime"].max()
        duration_h = 0.0
        if pd.notna(dt_min) and pd.notna(dt_max) and dt_max > dt_min:
            duration_h = round((dt_max - dt_min).total_seconds() / 3600.0, 2)

        area_km2_r = round(area_km2, 3)
        area_ha_r = round(area_km2 * 100.0, 1)
        max_temp_r = round(max_temp, 2)

        return {
            "event_id": f"FIRE_CLUSTER_{cid:03d}",
            "event_type": "Frente Activo",
            "location_name": self._resolve_local_toponym(cent_lat, cent_lon),
            "cluster_numeric_id": int(cid),
            "centroid_lat": round(cent_lat, 5),
            "centroid_lon": round(cent_lon, 5),
            "points_count": pts_count,
            "viirs_count": viirs_count,
            "modis_count": modis_count,
            "multisensor_confirmed": multisensor,
            "satellites_involved": satellites_involved,
            "frp_peak_mw": round(frp_peak_pass, 2),
            "frp_total_mw": round(frp_tot, 2),
            "frp_max_mw": round(frp_max, 2),
            "frp_mean_mw": round(frp_mean, 2),
            "frp_mean_density_mw_km2": round(frp_mean_density, 2),
            "fre_est_mj": round(fre_mj, 1),
            "temp_brightness_max_k": max_temp_r,
            "max_temp_k": max_temp_r,
            "mean_delta_temp_k": round(mean_delta, 2),
            "detection_area_km2": area_km2_r,
            "detection_area_ha": area_ha_r,
            "est_area_km2": area_km2_r,
            "est_area_ha": area_ha_r,
            "first_detected": dt_min,
            "last_detected": dt_max,
            "duration_hours": duration_h,
            "spread_vector_km": round(spread_km, 3),
            "spread_speed_kmh": round(speed_kmh, 3),
            "spread_azimuth_deg": round(azimuth, 1) if azimuth is not None else None,
            "spread_cardinal": cardinal,
            "severity_level": self._classify_severity(frp_peak_pass),
            "polygon_coords": poly_coords
        }

    def _calculate_convex_hull(self, lats: np.ndarray, lons: np.ndarray, cent_lat: float) -> Tuple[float, Optional[List[List[float]]]]:
        if len(lats) < 3:
            return 0.0, None

        # Proyección equirrectangular plana local a km
        lat_km = (lats - cent_lat) * 111.32
        lon_km = (lons - np.mean(lons)) * (111.32 * math.cos(math.radians(cent_lat)))
        pts_km = np.column_stack([lon_km, lat_km])

        try:
            hull = ConvexHull(pts_km)
            area_km2 = float(hull.volume)  # En 2D, hull.volume es el área
            hull_indices = hull.vertices.tolist()
            # Cerrar el polígono repitiendo el primer vértice
            hull_indices.append(hull_indices[0])
            poly_coords = [[round(float(lats[i]), 5), round(float(lons[i]), 5)] for i in hull_indices]
            return max(0.01, area_km2), poly_coords
        except Exception:
            return 0.0, None

    @staticmethod
    def _generate_buffer_polygon(cent_lat: float, cent_lon: float, area_km2: float, num_sides: int = 12) -> List[List[float]]:
        """
        Genera un polígono envolvente circular/regular cuando no hay suficientes puntos
        para Convex Hull (<3 detecciones), basado en el área equivalente de la huella de píxel.
        Retorna coordenadas en formato [[lat, lon], ...].
        """
        area = max(0.04, float(area_km2))
        radius_km = math.sqrt(area / math.pi)
        # Radio mínimo de 200m (huella VIIRS) y máximo de 4.0 km
        radius_km = max(0.20, min(radius_km, 4.0))

        coords = []
        lat_rad = math.radians(cent_lat)
        cos_lat = max(0.1, math.cos(lat_rad))

        for i in range(num_sides):
            angle = 2.0 * math.pi * i / num_sides
            d_lat = (radius_km * math.cos(angle)) / 111.32
            d_lon = (radius_km * math.sin(angle)) / (111.32 * cos_lat)
            coords.append([round(cent_lat + d_lat, 5), round(cent_lon + d_lon, 5)])

        coords.append(coords[0])
        return coords

    def _compute_kinematics(self, grp: pd.DataFrame, cent_lat: float, cent_lon: float) -> Tuple[float, float, Optional[float], str]:
        valid_dates = grp.dropna(subset=["acq_datetime"])
        if len(valid_dates) < 4:
            return 0.0, 0.0, None, "Estacionario"

        sorted_grp = valid_dates.sort_values(by="acq_datetime")
        mid = len(sorted_grp) // 2
        early = sorted_grp.iloc[:mid]
        late = sorted_grp.iloc[mid:]

        t_early = early["acq_datetime"].mean()
        t_late = late["acq_datetime"].mean()
        delta_hours = (t_late - t_early).total_seconds() / 3600.0

        if delta_hours < 0.5:
            return 0.0, 0.0, None, "Estacionario"

        lat1, lon1 = early["latitude"].mean(), early["longitude"].mean()
        lat2, lon2 = late["latitude"].mean(), late["longitude"].mean()

        # Distancia euclídea local en km
        d_lat = (lat2 - lat1) * 111.32
        d_lon = (lon2 - lon1) * (111.32 * math.cos(math.radians(cent_lat)))
        dist_km = math.sqrt(d_lat**2 + d_lon**2)

        if dist_km < 0.2:
            return round(dist_km, 3), 0.0, None, "Estacionario"

        speed = dist_km / delta_hours

        # Azimut en grados (0° Norte, 90° Este, 180° Sur, 270° Oeste)
        rad = math.atan2(d_lon, d_lat)
        azimuth = (math.degrees(rad) + 360.0) % 360.0

        cardinals = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        card_idx = int(((azimuth + 22.5) % 360.0) // 45)
        cardinal = cardinals[card_idx]

        return dist_km, speed, azimuth, cardinal

    @staticmethod
    def _classify_severity(frp_total_mw: float) -> str:
        if frp_total_mw >= 500.0:
            return "Crítico (Megaincendio)"
        elif frp_total_mw >= 150.0:
            return "Severidad Alta"
        elif frp_total_mw >= 30.0:
            return "Severidad Moderada"
        else:
            return "Severidad Baja"


# =============================================================================
# BLOQUE 4: VISUALIZACIÓN INTERACTIVA Y REPORTES CIENTÍFICOS
# =============================================================================

class FireAnalyticsVisualizer:
    """
    Genera mapas web interactivos (Folium) y paneles gráficos de alta resolución.
    """

    COLOR_MAP = {
        "Crítico (Megaincendio)": "#d73027",  # Rojo oscuro
        "Severidad Alta": "#f46d43",          # Naranja rojizo
        "Severidad Moderada": "#fdae61",      # Amarillo anaranjado
        "Severidad Baja": "#fee08b"           # Amarillo claro
    }

    def generate_interactive_map(self, df_points: pd.DataFrame, df_events: pd.DataFrame,
                                  output_html_path: str = "output/mapa_interactivo_nasa.html") -> str:
        if not FOLIUM_AVAILABLE:
            print("⚠️ Folium no está disponible. Omitiendo mapa interactivo HTML.")
            return ""

        if df_points.empty:
            print("⚠️ No hay puntos térmicos para graficar.")
            return ""

        os.makedirs(os.path.dirname(output_html_path) or ".", exist_ok=True)

        center_lat = float(df_points["latitude"].mean())
        center_lon = float(df_points["longitude"].mean())

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=8,
            tiles="CartoDB dark_matter",
            control_scale=True
        )

        # Capas base adicionales
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            name="🛰️ Imagen Satelital Esri",
            overlay=False
        ).add_to(m)

        folium.TileLayer(
            tiles="OpenStreetMap",
            name="🗺️ OpenStreetMap",
            overlay=False
        ).add_to(m)

        # 1. Capa Heatmap (FRP ponderado)
        heat_data = [[row["latitude"], row["longitude"], min(100.0, float(row["frp_mw"]))]
                     for _, row in df_points.iterrows() if row["frp_mw"] > 0]
        if heat_data:
            HeatMap(
                heat_data,
                name="🔥 Mapa de Calor Radiativo (FRP)",
                min_opacity=0.3,
                radius=15,
                blur=12,
                max_zoom=12
            ).add_to(m)

        # 2. Capa VIIRS (375 m)
        fg_viirs = folium.FeatureGroup(name="🟠 Focos VIIRS (Alta Res. 375m)", show=True)
        viirs_points = df_points[df_points["sensor_family"] == "VIIRS"]
        for _, row in viirs_points.iterrows():
            cid = row.get("cluster_id", -1)
            c_label = f"Cluster #{cid}" if cid >= 0 else "Foco Aislado"
            popup_html = f"""
            <div style="font-family: Arial; font-size: 12px; width: 220px;">
                <b style="color: #ff6600;">🛰️ VIIRS 375m ({row.get('satellite', 'N/A')})</b><br>
                <hr style="margin: 4px 0;">
                <b>Estado:</b> {c_label}<br>
                <b>Temp. Brillo (TI4):</b> {row['temp_ch4_k']} K<br>
                <b>Anomalía Térmica (ΔT):</b> {row['delta_temp_k']} K<br>
                <b>FRP:</b> {row['frp_mw']} MW ({row['frp_density_mw_km2']} MW/km²)<br>
                <b>Confianza:</b> {row['confidence_cat']} ({int(row['confidence_score']*100)}%)<br>
                <b>Fecha/Hora UTC:</b> {row['acq_datetime']}<br>
            </div>
            """
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=4,
                color="#ff5500",
                fill=True,
                fill_color="#ff8800",
                fill_opacity=0.75,
                weight=1,
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(fg_viirs)
        fg_viirs.add_to(m)

        # 3. Capa MODIS (1 km)
        fg_modis = folium.FeatureGroup(name="🔴 Focos MODIS (Res. Media 1km)", show=True)
        modis_points = df_points[df_points["sensor_family"] == "MODIS"]
        for _, row in modis_points.iterrows():
            cid = row.get("cluster_id", -1)
            c_label = f"Cluster #{cid}" if cid >= 0 else "Foco Aislado"
            popup_html = f"""
            <div style="font-family: Arial; font-size: 12px; width: 220px;">
                <b style="color: #cc0000;">🛰️ MODIS 1km ({row.get('satellite', 'N/A')})</b><br>
                <hr style="margin: 4px 0;">
                <b>Estado:</b> {c_label}<br>
                <b>Temp. Brillo (CH21/22):</b> {row['temp_ch4_k']} K<br>
                <b>Anomalía Térmica (ΔT):</b> {row['delta_temp_k']} K<br>
                <b>FRP:</b> {row['frp_mw']} MW ({row['frp_density_mw_km2']} MW/km²)<br>
                <b>Confianza:</b> {row['confidence_cat']} ({int(row['confidence_score']*100)}%)<br>
                <b>Fecha/Hora UTC:</b> {row['acq_datetime']}<br>
            </div>
            """
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=7,
                color="#cc0000",
                fill=True,
                fill_color="#ff2222",
                fill_opacity=0.7,
                weight=1.5,
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(fg_modis)
        fg_modis.add_to(m)

        # 4. Capa Perímetros de Incendios Consolidados (Convex Hull)
        fg_events = folium.FeatureGroup(name="📐 Perímetros de Incendio Consolidados", show=True)
        if not df_events.empty:
            clustered_events = df_events[df_events["cluster_numeric_id"] >= 0]
            for _, ev in clustered_events.iterrows():
                poly = ev.get("polygon_coords")
                sev = ev.get("severity_level", "Severidad Moderada")
                color = self.COLOR_MAP.get(sev, "#ff9900")

                popup_ev = f"""
                <div style="font-family: Arial; font-size: 12px; width: 275px;">
                    <b style="font-size: 14px; color: {color};">🚨 {ev['event_id']}</b><br>
                    <b>Zona / Localidad:</b> {ev.get('location_name', 'Sierras de Córdoba / San Luis')}<br>
                    <b>Nivel de Severidad:</b> {sev}<br>
                    <hr style="margin: 4px 0;">
                    <b>Confirmación:</b> {'✅ MODIS + VIIRS' if ev['multisensor_confirmed'] else '1 Solo Sensor'}<br>
                    <b>Detecciones:</b> {ev['points_count']} ({ev['viirs_count']} VIIRS, {ev['modis_count']} MODIS)<br>
                    <b>FRP Pico de Pasada:</b> {ev.get('frp_peak_mw', ev['frp_total_mw'])} MW (Máx píxel: {ev['frp_max_mw']} MW)<br>
                    <b>Energía Radiativa (FRE):</b> {ev.get('fre_est_mj', 0.0):,.1f} MJ<br>
                    <b>Temp. Máxima:</b> {ev['max_temp_k']} K<br>
                    <b>Superficie Estimada:</b> {ev['est_area_ha']} ha ({ev['est_area_km2']} km²)<br>
                    <b>Duración Observada:</b> {ev['duration_hours']} h<br>
                    <b>Dirección de Avance:</b> {ev['spread_cardinal']} ({ev['spread_vector_km']} km a {ev['spread_speed_kmh']} km/h)<br>
                </div>
                """

                if poly:
                    folium.Polygon(
                        locations=poly,
                        color=color,
                        weight=2.5,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.25,
                        popup=folium.Popup(popup_ev, max_width=300)
                    ).add_to(fg_events)

                # Marcador central del evento
                folium.Marker(
                    location=[ev["centroid_lat"], ev["centroid_lon"]],
                    icon=folium.Icon(color="red" if "Crítico" in sev else "orange", icon="fire", prefix="fa"),
                    popup=folium.Popup(popup_ev, max_width=300)
                ).add_to(fg_events)

        fg_events.add_to(m)

        # 5. Dashboard flotante de KPIs integrado en el mapa HTML
        total_pts = len(df_points)
        v_pts = len(viirs_points)
        m_pts = len(modis_points)
        v_pct = round((v_pts / total_pts) * 100, 1) if total_pts > 0 else 0
        m_pct = round((m_pts / total_pts) * 100, 1) if total_pts > 0 else 0
        peak_pass_frp = round(float(df_events["frp_peak_mw"].max()), 1) if (not df_events.empty and "frp_peak_mw" in df_events.columns) else round(float(df_points["frp_mw"].max()), 1)
        total_fre_mj = round(float(df_events["fre_est_mj"].sum()), 1) if (not df_events.empty and "fre_est_mj" in df_events.columns) else 0.0
        n_clusters = len(df_events[df_events["cluster_numeric_id"] >= 0]) if not df_events.empty else 0

        kpi_card_html = f"""
        <div style="
            position: fixed;
            top: 20px;
            right: 20px;
            width: 315px;
            background-color: rgba(20, 24, 33, 0.92);
            color: #ffffff;
            border: 1px solid #444;
            border-radius: 10px;
            padding: 14px 18px;
            z-index: 9999;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-shadow: 0 4px 15px rgba(0,0,0,0.6);
        ">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <span style="font-size: 15px; font-weight: bold; color: #ff6633;">🚀 NASA Space Apps</span>
                <span style="font-size: 11px; background: #334466; padding: 2px 6px; border-radius: 4px;">FIRMS</span>
            </div>
            <div style="font-size: 12px; color: #aaa; margin-bottom: 8px;">Caso: Sierras de Córdoba y San Luis</div>
            <hr style="border: 0; border-top: 1px solid #333; margin: 6px 0;">

            <div style="display: flex; justify-content: space-between; margin: 4px 0;">
                <span style="font-size: 12px; color: #ccc;">Focos Detectados:</span>
                <b style="font-size: 13px; color: #fff;">{total_pts}</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 4px 0;">
                <span style="font-size: 12px; color: #ff8833;">VIIRS 375m:</span>
                <b style="font-size: 12px;">{v_pts} ({v_pct}%)</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 4px 0;">
                <span style="font-size: 12px; color: #ff3333;">MODIS 1km:</span>
                <b style="font-size: 12px;">{m_pts} ({m_pct}%)</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 4px 0;">
                <span style="font-size: 12px; color: #ccc;">Frentes Consolidados:</span>
                <b style="font-size: 13px; color: #ffd700;">{n_clusters} incidentes</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 4px 0;">
                <span style="font-size: 12px; color: #ccc;">FRP Pico de Pasada:</span>
                <b style="font-size: 13px; color: #ff4444;">{peak_pass_frp:,} MW</b>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 4px 0;">
                <span style="font-size: 12px; color: #ccc;">Energía Total (FRE):</span>
                <b style="font-size: 12px; color: #ffaa44;">{total_fre_mj / 1000.0:,.2f} GJ</b>
            </div>
            <div style="font-size: 10px; color: #888; margin-top: 8px; text-align: center;">
                Clustering Haversine (DBSCAN) & Fusión Científica
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(kpi_card_html))

        # Banner de advertencia si los datos son simulados/sintéticos
        is_simulated = ("is_synthetic" in df_points.columns and df_points["is_synthetic"].any())
        if is_simulated:
            synthetic_banner_html = """
            <div style="
                position: fixed;
                bottom: 25px;
                left: 50%;
                transform: translateX(-50%);
                background-color: rgba(185, 28, 28, 0.95);
                color: #ffffff;
                border: 2px solid #f87171;
                border-radius: 8px;
                padding: 10px 22px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 0.5px;
                z-index: 99999;
                box-shadow: 0 4px 15px rgba(0,0,0,0.6);
                text-align: center;
            ">
                ⚠️ MODO SIMULACIÓN — DATOS SINTÉTICOS DE PRUEBA (NO UTILIZAR PARA EMERGENCIAS REALES)
            </div>
            """
            m.get_root().html.add_child(folium.Element(synthetic_banner_html))

        # Controles
        Fullscreen().add_to(m)
        folium.LayerControl(position="topleft", collapsed=False).add_to(m)

        m.save(output_html_path)
        print(f"🗺️ Mapa interactivo generado con éxito en: {output_html_path}")
        return output_html_path

    def generate_statistical_charts(self, df_points: pd.DataFrame, df_events: pd.DataFrame,
                                     output_png_path: str = "output/analisis_estadistico_sensores.png") -> str:
        if not PLT_AVAILABLE:
            print("⚠️ Matplotlib/Seaborn no están disponibles. Omitiendo gráfico estadístico.")
            return ""

        if df_points.empty:
            return ""

        os.makedirs(os.path.dirname(output_png_path) or ".", exist_ok=True)

        sns.set_theme(style="darkgrid")
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle("NASA Space Apps Challenge: Comparativa Científica MODIS vs VIIRS", fontsize=18, fontweight="bold", y=0.98)

        # 1. Distribución de Temperatura de Brillo CH4
        ax1 = axes[0, 0]
        sns.kdeplot(data=df_points, x="temp_ch4_k", hue="sensor_family", common_norm=False, fill=True,
                    palette={"VIIRS": "#ff7700", "MODIS": "#cc0000"}, ax=ax1, alpha=0.4)
        ax1.set_title("1. Distribución de Temperatura Térmica (Canal ~4 µm)", fontsize=13, fontweight="bold")
        ax1.set_xlabel("Temperatura de Brillo (Kelvin)")
        ax1.set_ylabel("Densidad de Probabilidad")

        # 2. Densidad de Potencia Radiativa (FRP Density MW/km²)
        ax2 = axes[0, 1]
        df_frp_filter = df_points[(df_points["frp_density_mw_km2"] > 0) & (df_points["frp_density_mw_km2"] < 200)]
        if not df_frp_filter.empty:
            sns.boxplot(data=df_frp_filter, x="sensor_family", y="frp_density_mw_km2", hue="daynight",
                        palette="Set2", ax=ax2)
            ax2.set_title("2. Densidad de FRP (MW/km²) por Sensor y Turno (Día/Noche)", fontsize=13, fontweight="bold")
            ax2.set_xlabel("Familia de Sensor")
            ax2.set_ylabel("FRP Densidad (MW/km²)")

        # 3. Distribución de Niveles de Confianza Armonizados
        ax3 = axes[1, 0]
        conf_counts = df_points.groupby(["sensor_family", "confidence_cat"]).size().unstack(fill_value=0)
        conf_counts.plot(kind="bar", stacked=True, color=["#fee08b", "#fdae61", "#d73027"], ax=ax3, rot=0)
        ax3.set_title("3. Detecciones por Nivel de Confianza Armonizado", fontsize=13, fontweight="bold")
        ax3.set_xlabel("Sensor")
        ax3.set_ylabel("Cantidad de Píxeles Térmicos")
        ax3.legend(title="Confianza")

        # 4. Top 8 Frentes de Fuego por Potencia Radiativa Pico
        ax4 = axes[1, 1]
        if not df_events.empty:
            top_events = df_events[df_events["cluster_numeric_id"] >= 0].head(8)
            if not top_events.empty:
                sns.barplot(data=top_events, x="frp_peak_mw", y="event_id", hue="severity_level",
                            palette=self.COLOR_MAP, dodge=False, ax=ax4)
                ax4.set_title("4. Frentes Activos por Potencia Radiativa Pico (MW)", fontsize=13, fontweight="bold")
                ax4.set_xlabel("Potencia Radiativa Pico por Pasada (MW)")
                ax4.set_ylabel("ID de Incendio")
                ax4.legend(title="Severidad", loc="lower right")
            else:
                ax4.text(0.5, 0.5, "No se consolidaron clusters suficientes", ha="center", va="center")
        else:
            ax4.text(0.5, 0.5, "Sin eventos", ha="center", va="center")

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(output_png_path, dpi=200)
        plt.close()
        print(f"📊 Panel estadístico generado con éxito en: {output_png_path}")
        return output_png_path


# =============================================================================
# BLOQUE 5: CALENDARIO DE ACTIVIDAD DE QUEMAS (BURNING ACTIVITY CALENDAR)
# =============================================================================

class BurningActivityCalendar:
    """
    Motor del Calendario de Actividad de Quemas (Burning Activity Calendar)
    y Análisis de Línea Base Histórica (2000-2026).
    Compara detecciones armonizadas de la pasada actual contra el régimen
    climatológico estacional esperado (semanas ecológicas 1 a 52).
    """

    REGIONAL_BASELINES = {
        "Sierras_Cordoba_SanLuis": {
            "name": "Sierras de Córdoba y San Luis (Argentina)",
            "peak_season_months": ["Agosto", "Septiembre", "Octubre"],
            "peak_weeks": list(range(31, 45)),
            "annual_expected_hotspots": 2450,
        },
        "California": {
            "name": "California & Western US",
            "peak_season_months": ["Julio", "Agosto", "Septiembre", "Octubre"],
            "peak_weeks": list(range(27, 43)),
            "annual_expected_hotspots": 8500,
        }
    }

    @classmethod
    def get_baseline_curve(cls, region_key: str = "Sierras_Cordoba_SanLuis") -> List[Dict[str, Any]]:
        is_cordoba = "cordoba" in region_key.lower() or "sanluis" in region_key.lower() or "argentina" in region_key.lower()
        curve = []
        month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        for w in range(1, 53):
            if is_cordoba:
                if 31 <= w <= 42:
                    mean_val = 110.0 + 80.0 * math.sin((w - 31) / 11.0 * math.pi)
                    std_val = mean_val * 0.35
                elif 21 <= w <= 30 or 43 <= w <= 46:
                    mean_val = 35.0 + 20.0 * math.sin((w - 21) / 10.0 * math.pi)
                    std_val = mean_val * 0.40
                else:
                    mean_val = 12.0 + 5.0 * math.cos(w / 52.0 * 2 * math.pi)
                    std_val = max(4.0, mean_val * 0.45)
            else:
                if 27 <= w <= 42:
                    mean_val = 180.0 + 120.0 * math.sin((w - 27) / 15.0 * math.pi)
                    std_val = mean_val * 0.40
                elif 20 <= w <= 26 or 43 <= w <= 47:
                    mean_val = 50.0 + 30.0 * math.sin((w - 20) / 7.0 * math.pi)
                    std_val = mean_val * 0.45
                else:
                    mean_val = 15.0
                    std_val = 6.0

            approx_month_idx = min(11, int((w - 1) / 4.33))
            curve.append({
                "week": w,
                "month": month_names[approx_month_idx],
                "baseline_mean": round(mean_val, 1),
                "baseline_std": round(std_val, 1)
            })
        return curve

    @classmethod
    def compute_calendar(cls, df_points: pd.DataFrame, area: str, year: int = 2026) -> Dict[str, Any]:
        """
        Construye la matriz y métricas del Burning Activity Calendar.
        """
        reg_key = "Sierras_Cordoba_SanLuis"
        if any(coord in area for coord in ["-124", "32", "37", "-119", "-120"]):
            reg_key = "California"

        baseline = cls.get_baseline_curve(reg_key)
        baseline_map = {b["week"]: b for b in baseline}

        observed_by_week = {}
        observed_by_month = {}
        month_names_full = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        current_active_week = None
        if not df_points.empty and "acq_datetime" in df_points.columns:
            valid_dt = df_points.dropna(subset=["acq_datetime"]).copy()
            if not valid_dt.empty:
                valid_dt["week_num"] = valid_dt["acq_datetime"].dt.isocalendar().week
                valid_dt["month_num"] = valid_dt["acq_datetime"].dt.month

                for _, r in valid_dt.iterrows():
                    w = int(r["week_num"])
                    m = int(r["month_num"])
                    current_active_week = w
                    equiv = float(r.get("viirs_equiv_count", 1.0))
                    frp = float(r.get("frp_mw", 0.0))

                    if w not in observed_by_week:
                        observed_by_week[w] = {"raw_count": 0, "harmonized_count": 0.0, "total_frp": 0.0}
                    observed_by_week[w]["raw_count"] += 1
                    observed_by_week[w]["harmonized_count"] += equiv
                    observed_by_week[w]["total_frp"] += frp

                    if m not in observed_by_month:
                        observed_by_month[m] = {"raw_count": 0, "harmonized_count": 0.0, "total_frp": 0.0}
                    observed_by_month[m]["raw_count"] += 1
                    observed_by_month[m]["harmonized_count"] += equiv
                    observed_by_month[m]["total_frp"] += frp

        if current_active_week is None:
            current_active_week = datetime.utcnow().isocalendar()[1]

        weeks_data = []
        for b in baseline:
            w = b["week"]
            obs = observed_by_week.get(w, {"raw_count": 0, "harmonized_count": 0.0, "total_frp": 0.0})
            mean_b = b["baseline_mean"]
            std_b = b["baseline_std"]
            h_cnt = round(obs["harmonized_count"], 1)
            raw_cnt = obs["raw_count"]

            if raw_cnt > 0:
                z_score = round((h_cnt - mean_b) / max(1.0, std_b), 2)
                if z_score >= 2.0:
                    status = "Anomalía Extrema"
                    tier = 4
                    color = "#d73027"
                elif z_score >= 1.0:
                    status = "Actividad Alta"
                    tier = 3
                    color = "#f46d43"
                elif z_score >= 0.0:
                    status = "Normal / Temporada Típica"
                    tier = 2
                    color = "#fdae61"
                else:
                    status = "Por Debajo de la Media"
                    tier = 1
                    color = "#fee08b"
            else:
                z_score = 0.0
                status = "Sin Detecciones Activas"
                tier = 0
                color = "#1e293b"

            weeks_data.append({
                "week": w,
                "month": b["month"],
                "baseline_mean": mean_b,
                "baseline_std": std_b,
                "observed_raw": raw_cnt,
                "observed_harmonized": h_cnt,
                "observed_frp_mw": round(obs["total_frp"], 1),
                "z_score": z_score,
                "status": status,
                "tier": tier,
                "color": color,
                "is_current": (w == current_active_week)
            })

        monthly_summary = []
        for m_idx in range(1, 13):
            m_name = month_names_full[m_idx - 1]
            obs_m = observed_by_month.get(m_idx, {"raw_count": 0, "harmonized_count": 0.0, "total_frp": 0.0})
            m_weeks = [w for w in weeks_data if int((w["week"] - 1) / 4.33) == (m_idx - 1)]
            b_mean_sum = round(sum(w["baseline_mean"] for w in m_weeks), 1)

            monthly_summary.append({
                "month_num": m_idx,
                "month_name": m_name,
                "baseline_expected": b_mean_sum,
                "observed_harmonized": round(obs_m["harmonized_count"], 1),
                "observed_raw": obs_m["raw_count"],
                "is_peak_season": m_name in ["Agosto", "Septiembre", "Octubre"] if "cordoba" in reg_key.lower() else m_name in ["Julio", "Agosto", "Septiembre", "Octubre"]
            })

        curr_week_info = baseline_map.get(current_active_week, baseline[0])
        curr_obs = observed_by_week.get(current_active_week, {"raw_count": 0, "harmonized_count": 0.0, "total_frp": 0.0})
        curr_z = round((curr_obs["harmonized_count"] - curr_week_info["baseline_mean"]) / max(1.0, curr_week_info["baseline_std"]), 2)

        return {
            "region": reg_key,
            "region_display_name": cls.REGIONAL_BASELINES.get(reg_key, {}).get("name", reg_key),
            "target_year": year,
            "current_week": current_active_week,
            "current_week_anomaly_z": curr_z,
            "historical_peak_period": "Agosto – Octubre (Semanas 31 a 44)" if "cordoba" in reg_key.lower() else "Julio – Octubre (Semanas 27 a 43)",
            "seasonal_risk_index": 82 if (30 <= current_active_week <= 44) else 35,
            "total_harmonized_hotspots": round(sum(w["observed_harmonized"] for w in weeks_data), 1),
            "total_raw_hotspots": sum(w["observed_raw"] for w in weeks_data),
            "weeks": weeks_data,
            "months": monthly_summary
        }


# =============================================================================
# BLOQUE 6: EXPORTACIÓN ABIERTA (GEOJSON Y CSV)
# =============================================================================

class GeoExporter:
    """
    Exporta datos en formatos abiertos estándar (GeoJSON, CSV)
    para interoperabilidad con QGIS, ArcGIS y centros de mando.
    """

    @staticmethod
    def export_csv(df_points: pd.DataFrame, points_csv_path: str,
                   df_events: pd.DataFrame, events_csv_path: str):
        os.makedirs(os.path.dirname(points_csv_path) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(events_csv_path) or ".", exist_ok=True)

        if not df_points.empty:
            df_points.to_csv(points_csv_path, index=False)
            print(f"💾 Puntos normalizados exportados a: {points_csv_path}")

        if not df_events.empty:
            # Excluir polígono crudo del CSV para mantenerlo limpio
            cols = [c for c in df_events.columns if c != "polygon_coords"]
            df_events[cols].to_csv(events_csv_path, index=False)
            print(f"💾 Eventos consolidados exportados a: {events_csv_path}")

    @staticmethod
    def export_geojson(df_events: pd.DataFrame, df_points: pd.DataFrame,
                       geojson_path: str = "output/perimetros_incendios.geojson"):
        os.makedirs(os.path.dirname(geojson_path) or ".", exist_ok=True)

        features = []

        # 1. Polígonos de eventos consolidados
        if not df_events.empty:
            for _, ev in df_events.iterrows():
                poly = ev.get("polygon_coords")
                props = {
                    "event_id": str(ev["event_id"]),
                    "event_type": str(ev["event_type"]),
                    "location_name": str(ev.get("location_name", "Sierras de Córdoba / San Luis")),
                    "severity": str(ev["severity_level"]),
                    "severity_level": str(ev["severity_level"]),
                    "cluster_numeric_id": int(ev.get("cluster_numeric_id", -1)),
                    "centroid_lat": float(ev["centroid_lat"]),
                    "centroid_lon": float(ev["centroid_lon"]),
                    "frp_peak_mw": float(ev.get("frp_peak_mw", ev["frp_total_mw"])),
                    "frp_total_mw": float(ev["frp_total_mw"]),
                    "frp_max_mw": float(ev.get("frp_max_mw", ev["frp_total_mw"])),
                    "fre_est_mj": float(ev.get("fre_est_mj", 0.0)),
                    "detection_area_ha": float(ev.get("detection_area_ha", ev["est_area_ha"])),
                    "est_area_ha": float(ev["est_area_ha"]),
                    "est_area_km2": float(ev.get("est_area_km2", ev.get("detection_area_km2", 0.0))),
                    "detections_count": int(ev["points_count"]),
                    "viirs_count": int(ev["viirs_count"]),
                    "modis_count": int(ev["modis_count"]),
                    "multisensor_confirmed": bool(ev.get("multisensor_confirmed", False)),
                    "satellites_involved": str(ev.get("satellites_involved", "N/A")),
                    "first_detected": str(ev["first_detected"]) if pd.notna(ev.get("first_detected")) else None,
                    "last_detected": str(ev["last_detected"]) if pd.notna(ev.get("last_detected")) else None,
                    "duration_hours": float(ev.get("duration_hours", 0.0)),
                    "spread_vector_km": float(ev.get("spread_vector_km", 0.0)),
                    "spread_speed_kmh": float(ev["spread_speed_kmh"]),
                    "spread_azimuth_deg": float(ev["spread_azimuth_deg"]) if pd.notna(ev.get("spread_azimuth_deg")) else None,
                    "spread_cardinal": str(ev["spread_cardinal"]),
                    "temp_brightness_max_k": float(ev.get("temp_brightness_max_k", ev.get("max_temp_k", 0.0))),
                    "mean_delta_temp_k": float(ev.get("mean_delta_temp_k", 0.0))
                }

                if poly and len(poly) >= 3:
                    # Formato GeoJSON: [lon, lat]
                    coords_geojson = [[round(p[1], 5), round(p[0], 5)] for p in poly]
                    feat = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [coords_geojson]
                        },
                        "properties": props
                    }
                    features.append(feat)
                else:
                    feat = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [float(ev["centroid_lon"]), float(ev["centroid_lat"])]
                        },
                        "properties": props
                    }
                    features.append(feat)

        geojson_doc = {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }

        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_doc, f, indent=2, ensure_ascii=False, default=str)

        print(f"🌍 GeoJSON espacial generado en: {geojson_path} ({len(features)} geometrías)")
        return geojson_path

    @staticmethod
    def export_dashboard_json(
        df_events: pd.DataFrame,
        df_points: pd.DataFrame,
        area: str,
        day_range: int,
        date_str: Optional[str] = None,
        json_path: str = "output/dashboard_data.json",
        calendar_data: Optional[Dict[str, Any]] = None,
        cross_calib_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Exporta un archivo JSON estructurado y ligero para consumo directo
        por el Frontend (Portal Web AURA-FIRE, Calendario de Quemas y App Táctica).
        """
        os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)

        is_synth = bool("is_synthetic" in df_points.columns and df_points["is_synthetic"].any()) if not df_points.empty else False
        total_pts = len(df_points)
        viirs_cnt = int((df_points["sensor_family"] == "VIIRS").sum()) if not df_points.empty else 0
        modis_cnt = int((df_points["sensor_family"] == "MODIS").sum()) if not df_points.empty else 0
        total_harmonized_hotspots = round(float(df_points["viirs_equiv_count"].sum()), 1) if ("viirs_equiv_count" in df_points.columns and not df_points.empty) else float(total_pts)

        if calendar_data is None:
            calendar_data = BurningActivityCalendar.compute_calendar(df_points, area)
        if cross_calib_data is None:
            cross_calib_data = ModisViirsHarmonizer.compute_cross_sensor_calibration(df_points)

        active_clusters = df_events[df_events["cluster_numeric_id"] >= 0] if not df_events.empty else pd.DataFrame()
        isolated_events = df_events[df_events["cluster_numeric_id"] < 0] if not df_events.empty else pd.DataFrame()

        peak_frp = float(df_events["frp_peak_mw"].max()) if (not df_events.empty and "frp_peak_mw" in df_events.columns) else 0.0
        total_fre = float(df_events["fre_est_mj"].sum()) if (not df_events.empty and "fre_est_mj" in df_events.columns) else 0.0
        total_area_ha = float(active_clusters["detection_area_ha"].sum()) if (not active_clusters.empty and "detection_area_ha" in active_clusters.columns) else 0.0
        multisensor_cnt = int(active_clusters["multisensor_confirmed"].sum()) if not active_clusters.empty else 0

        # Desglose por satélite
        sat_col = "satellite_name" if "satellite_name" in df_points.columns else "satellite"
        sat_breakdown = {}
        if not df_points.empty and sat_col in df_points.columns:
            counts = df_points[sat_col].value_counts()
            for sat_k, cnt_v in counts.items():
                sat_breakdown[str(sat_k)] = {
                    "count": int(cnt_v),
                    "percentage": round((int(cnt_v) / total_pts) * 100.0, 2) if total_pts > 0 else 0.0
                }

        # Serie temporal por pasada satelital
        temporal_series = []
        if not df_points.empty and "acq_datetime" in df_points.columns:
            valid_t = df_points.dropna(subset=["acq_datetime"]).copy()
            if not valid_t.empty:
                valid_t["pass_hour"] = valid_t["acq_datetime"].dt.strftime("%Y-%m-%d %H:00")
                grouped_t = valid_t.groupby(["pass_hour", "sensor_family"]).agg(
                    detections=("frp_mw", "count"),
                    pass_frp_mw=("frp_mw", "sum"),
                    max_brightness_k=("temp_ch4_k", "max")
                ).reset_index()
                for _, trow in grouped_t.iterrows():
                    temporal_series.append({
                        "timestamp_hour_utc": str(trow["pass_hour"]),
                        "sensor_family": str(trow["sensor_family"]),
                        "detections": int(trow["detections"]),
                        "pass_frp_mw": round(float(trow["pass_frp_mw"]), 2),
                        "max_brightness_k": round(float(trow["max_brightness_k"]), 2)
                    })

        # Lista de eventos principales para el frontend
        events_list = []
        if not df_events.empty:
            for _, ev in df_events.iterrows():
                ev_dict = {
                    "event_id": str(ev["event_id"]),
                    "event_type": str(ev["event_type"]),
                    "location_name": str(ev.get("location_name", "Sierras de Córdoba / San Luis")),
                    "centroid_lat": float(ev["centroid_lat"]),
                    "centroid_lon": float(ev["centroid_lon"]),
                    "points_count": int(ev["points_count"]),
                    "viirs_count": int(ev["viirs_count"]),
                    "modis_count": int(ev["modis_count"]),
                    "multisensor_confirmed": bool(ev["multisensor_confirmed"]),
                    "satellites_involved": str(ev.get("satellites_involved", "N/A")),
                    "frp_peak_mw": float(ev.get("frp_peak_mw", ev["frp_total_mw"])),
                    "fre_est_mj": float(ev.get("fre_est_mj", 0.0)),
                    "temp_brightness_max_k": float(ev.get("temp_brightness_max_k", ev["max_temp_k"])),
                    "mean_delta_temp_k": float(ev["mean_delta_temp_k"]),
                    "detection_area_ha": float(ev.get("detection_area_ha", ev["est_area_ha"])),
                    "first_detected": str(ev["first_detected"]),
                    "last_detected": str(ev["last_detected"]),
                    "duration_hours": float(ev["duration_hours"]),
                    "spread_vector_km": float(ev["spread_vector_km"]),
                    "spread_speed_kmh": float(ev["spread_speed_kmh"]),
                    "spread_azimuth_deg": float(ev["spread_azimuth_deg"]) if pd.notna(ev["spread_azimuth_deg"]) else None,
                    "spread_cardinal": str(ev["spread_cardinal"]),
                    "severity_level": str(ev["severity_level"]),
                    "polygon_coords": ev.get("polygon_coords")
                }
                events_list.append(ev_dict)

        # Lista de puntos térmicos armonizados para el visor geoespacial
        points_list = []
        if not df_points.empty:
            for _, pt in df_points.iterrows():
                points_list.append({
                    "latitude": round(float(pt["latitude"]), 5),
                    "longitude": round(float(pt["longitude"]), 5),
                    "sensor_family": str(pt.get("sensor_family", "N/A")),
                    "satellite_name": str(pt.get("satellite_name", pt.get("satellite", "N/A"))),
                    "frp_mw": round(float(pt.get("frp_mw", 0.0)), 2),
                    "frp_density_mw_km2": round(float(pt.get("frp_density_mw_km2", 0.0)), 2),
                    "temp_ch4_k": round(float(pt.get("temp_ch4_k", 0.0)), 2),
                    "delta_temp_k": round(float(pt.get("delta_temp_k", 0.0)), 2),
                    "confidence_cat": str(pt.get("confidence_cat", "Nominal")),
                    "confidence_score": round(float(pt.get("confidence_score", 0.5)), 2),
                    "pixel_area_km2": round(float(pt.get("pixel_area_km2", 0.14)), 4),
                    "acq_datetime": str(pt.get("acq_datetime", "")),
                    "cluster_id": int(pt.get("cluster_id", -1))
                })

        dashboard_payload = {
            "metadata": {
                "generated_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "bbox": area,
                "date_reference": date_str,
                "day_range": day_range,
                "is_synthetic": is_synth,
                "total_detections": total_pts,
                "active_fronts_count": len(active_clusters),
                "isolated_hotspots_count": len(isolated_events)
            },
            "kpis": {
                "viirs_detections": viirs_cnt,
                "modis_detections": modis_cnt,
                "harmonized_equivalent_detections": total_harmonized_hotspots,
                "peak_pass_frp_mw": round(peak_frp, 2),
                "total_estimated_fre_mj": round(total_fre, 1),
                "total_detection_envelope_ha": round(total_area_ha, 1),
                "multisensor_confirmed_fronts": multisensor_cnt
            },
            "satellite_breakdown": sat_breakdown,
            "temporal_series": temporal_series,
            "events": events_list,
            "points": points_list,
            "burning_activity_calendar": calendar_data,
            "cross_sensor_calibration": cross_calib_data
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_payload, f, indent=2, ensure_ascii=False, default=str)

        print(f"📡 Datos escalables para Frontend exportados a: {json_path}")
        return json_path


# =============================================================================
# BLOQUE 6: EJECUTOR PRINCIPAL (CLI & ORQUESTADOR)
# =============================================================================

def run_pipeline(
    area: str = DEFAULT_ARGENTINA_BBOX,
    day_range: int = 5,
    date: Optional[str] = None,
    map_key: Optional[str] = None,
    eps_km: float = 2.5,
    output_dir: str = "output",
    force_offline: bool = False
) -> Dict[str, Any]:
    """
    Ejecuta el ciclo de vida completo del análisis de focos satelitales.
    """
    if map_key is None:
        map_key = DEFAULT_MAP_KEY

    print("\n" + "="*70)
    print("🛰️  INICIANDO PIPELINE DE FUSIÓN Y ANÁLISIS MODIS / VIIRS (NASA SPACE APPS)")
    print("="*70)
    print(f"📍 Área geográfica (Bounding Box): {area}")
    print(f"📅 Rango de días: {day_range}" + (f" (Fecha base: {date})" if date else " (Tiempo reciente NRT)"))
    print(f"📐 Radio geodésico de agrupación (DBSCAN): {eps_km} km")
    print(f"📁 Directorio de resultados: {output_dir}\n")

    os.makedirs(output_dir, exist_ok=True)

    # 1. Ingesta
    ingestor = FIRMSDataIngestor(map_key=map_key, cache_dir="data/raw")
    if force_offline:
        df_raw = ingestor.generate_calibrated_fallback(area)
    else:
        df_raw = ingestor.fetch_all(area=area, day_range=day_range, date=date)

    if df_raw.empty:
        print("ℹ️ No se registraron focos térmicos para procesar en la ventana consultada.")
        return {}

    # 2. Armonización
    harmonizer = ModisViirsHarmonizer()
    df_clean = harmonizer.harmonize(df_raw)

    if df_clean.empty:
        print("❌ Error: No se obtuvieron datos válidos tras la armonización.")
        return {}

    # 3. Clustering Espaciotemporal
    clusterer = FireEventClusterer(eps_km=eps_km, min_samples=2)
    df_clustered = clusterer.cluster_points(df_clean)
    df_events = clusterer.compute_event_metrics(df_clustered)

    # 4. Calendario de Actividad de Quemas y Calibración Inter-Sensor
    calendar_data = BurningActivityCalendar.compute_calendar(df_clustered, area)
    cross_calib_data = ModisViirsHarmonizer.compute_cross_sensor_calibration(df_clustered)

    # 5. Visualización
    visualizer = FireAnalyticsVisualizer()
    map_path = os.path.join(output_dir, "mapa_interactivo_nasa.html")
    chart_path = os.path.join(output_dir, "analisis_estadistico_sensores.png")

    visualizer.generate_interactive_map(df_clustered, df_events, map_path)
    visualizer.generate_statistical_charts(df_clustered, df_events, chart_path)

    # 6. Exportación Abierta y Capa de Datos para Frontend
    points_csv = os.path.join(output_dir, "focos_calor_normalizados.csv")
    events_csv = os.path.join(output_dir, "eventos_incendio_consolidados.csv")
    geojson_path = os.path.join(output_dir, "perimetros_incendios.geojson")
    dashboard_json_path = os.path.join(output_dir, "dashboard_data.json")

    GeoExporter.export_csv(df_clustered, points_csv, df_events, events_csv)
    GeoExporter.export_geojson(df_events, df_clustered, geojson_path)
    GeoExporter.export_dashboard_json(
        df_events=df_events,
        df_points=df_clustered,
        area=area,
        day_range=day_range,
        date_str=date,
        json_path=dashboard_json_path,
        calendar_data=calendar_data,
        cross_calib_data=cross_calib_data
    )

    # 7. Generación de la App Táctica Mobile-First y de Supervivencia
    tactical_app_path = os.path.join(output_dir, "app_tactica_mobile.html")
    try:
        from generar_app_tactica import main as gen_tactical_app
        gen_tactical_app()
    except Exception as e:
        print(f"⚠️ Nota sobre app_tactica_mobile.html: {e}")

    print("\n" + "="*70)
    print("🎉 PIPELINE COMPLETADO EXITOSAMENTE")
    print("="*70)
    print(f"📊 Focos térmicos procesados: {len(df_clustered)} ({int((df_clustered['sensor_family'] == 'VIIRS').sum())} VIIRS, {int((df_clustered['sensor_family'] == 'MODIS').sum())} MODIS)")
    print(f"🔥 Frentes de fuego consolidados: {len(df_events[df_events['cluster_numeric_id'] >= 0])}")
    print(f"📅 Calendario de Actividad: Semana {calendar_data['current_week']} | Z-Score: {calendar_data['current_week_anomaly_z']:+.2f}σ | Riesgo: {calendar_data['seasonal_risk_index']}%")
    print(f"🛰️ Calibración Inter-Sensor: Multiplicador VIIRS/MODIS = {cross_calib_data.get('empirical_count_ratio', 4.0)}x")
    print(f"🌍 Archivos listos en '{output_dir}/':")
    print(f"   - {map_path}")
    print(f"   - {chart_path}")
    print(f"   - {points_csv}")
    print(f"   - {events_csv}")
    print(f"   - {geojson_path}")
    print(f"   - {dashboard_json_path}")
    print(f"   - {tactical_app_path}")
    print("="*70 + "\n")

    return {
        "df_points": df_clustered,
        "df_events": df_events,
        "calendar_data": calendar_data,
        "cross_calib_data": cross_calib_data,
        "map_path": map_path,
        "chart_path": chart_path,
        "points_csv": points_csv,
        "events_csv": events_csv,
        "geojson_path": geojson_path,
        "dashboard_json_path": dashboard_json_path,
        "tactical_app_path": tactical_app_path
    }


def main():
    # Pre-procesar sys.argv para permitir coordenadas negativas en --bbox sin usar '='
    sanitized_argv = []
    idx = 0
    while idx < len(sys.argv):
        curr_arg = sys.argv[idx]
        if curr_arg in ["--bbox", "-b"] and (idx + 1) < len(sys.argv):
            next_val = sys.argv[idx + 1]
            if next_val.startswith("-") and not next_val.startswith("--"):
                sanitized_argv.append(f"{curr_arg}={next_val}")
                idx += 2
                continue
        sanitized_argv.append(curr_arg)
        idx += 1
    sys.argv = sanitized_argv

    parser = argparse.ArgumentParser(description="Pipeline de Fusión y Análisis MODIS/VIIRS para NASA Space Apps")
    parser.add_argument("--bbox", type=str, default=DEFAULT_ARGENTINA_BBOX,
                        help="Bounding box: min_lon,min_lat,max_lon,max_lat (def: Sierras de Córdoba/San Luis, Argentina)")
    parser.add_argument("--days", type=int, default=5,
                        help="Días históricos hacia atrás (1 a 10)")
    parser.add_argument("--date", type=str, default=None,
                        help="Fecha histórica en formato YYYY-MM-DD (opcional)")
    parser.add_argument("--key", type=str, default=DEFAULT_MAP_KEY,
                        help="NASA FIRMS MAP_KEY (def: variable de entorno FIRMS_MAP_KEY)")
    parser.add_argument("--eps", type=float, default=2.5,
                        help="Radio en km para clustering DBSCAN (def: 2.5 km)")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Carpeta de salida para mapas y reportes")
    parser.add_argument("--offline", action="store_true",
                        help="Forzar generación de datos sintéticos de demostración sin conectar a API")

    args = parser.parse_args()

    run_pipeline(
        area=args.bbox,
        day_range=args.days,
        date=args.date,
        map_key=args.key,
        eps_km=args.eps,
        output_dir=args.output_dir,
        force_offline=args.offline
    )


if __name__ == "__main__":
    main()
