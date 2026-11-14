#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para el Pipeline de Fusión y Análisis MODIS & VIIRS
(NASA Space Apps Challenge).
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

# Añadir directorio raíz al PATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pipeline_incendios_nasa import (
    FIRMSDataIngestor,
    ModisViirsHarmonizer,
    FireEventClusterer,
    BurningActivityCalendar,
    GeoExporter,
    DEFAULT_ARGENTINA_BBOX
)


class TestModisViirsPipeline(unittest.TestCase):

    def setUp(self):
        # Datos de prueba simulando filas exactas de MODIS y VIIRS
        self.raw_data = pd.DataFrame([
            # Fila 1: VIIRS (NOAA-20)
            {
                "latitude": 37.75,
                "longitude": -122.41,
                "bright_ti4": 345.5,
                "bright_ti5": 298.2,
                "scan": 0.4,
                "track": 0.36,
                "acq_date": "2026-10-01",
                "acq_time": "1345",
                "satellite": "NOAA-20",
                "confidence": "h",
                "version": "2.0NRT",
                "frp": 15.6,
                "daynight": "D",
                "sensor_source": "VIIRS_NOAA20_NRT"
            },
            # Fila 2: VIIRS vecino (Cluster 1)
            {
                "latitude": 37.76,
                "longitude": -122.42,
                "bright_ti4": 352.0,
                "bright_ti5": 301.0,
                "scan": 0.38,
                "track": 0.37,
                "acq_date": "2026-10-01",
                "acq_time": "1346",
                "satellite": "NOAA-20",
                "confidence": "n",
                "version": "2.0NRT",
                "frp": 22.0,
                "daynight": "D",
                "sensor_source": "VIIRS_NOAA20_NRT"
            },
            # Fila 3: MODIS (Aqua) en el mismo evento (co-detección)
            {
                "latitude": 37.755,
                "longitude": -122.415,
                "brightness": 328.4,
                "bright_t31": 295.1,
                "scan": 1.2,
                "track": 1.1,
                "acq_date": "2026-10-01",
                "acq_time": "1410",
                "satellite": "Aqua",
                "confidence": 85,
                "version": "6.1NRT",
                "frp": 45.2,
                "daynight": "D",
                "sensor_source": "MODIS_NRT"
            },
            # Fila 4: Foco lejano aislado (a más de 100 km)
            {
                "latitude": 39.50,
                "longitude": -120.10,
                "bright_ti4": 315.0,
                "bright_ti5": 290.0,
                "scan": 0.4,
                "track": 0.4,
                "acq_date": "2026-10-01",
                "acq_time": "1345",
                "satellite": "SNPP",
                "confidence": "l",
                "version": "2.0NRT",
                "frp": 5.0,
                "daynight": "D",
                "sensor_source": "VIIRS_SNPP_NRT"
            }
        ])

    def test_harmonization_preserves_both_sensors(self):
        """Verifica que ningún sensor se pierda y las columnas se unifiquen sin NaNs."""
        harmonizer = ModisViirsHarmonizer()
        df_clean = harmonizer.harmonize(self.raw_data)

        # Deben conservarse las 4 filas
        self.assertEqual(len(df_clean), 4)

        # MODIS y VIIRS deben estar presentes
        families = set(df_clean["sensor_family"])
        self.assertIn("VIIRS", families)
        self.assertIn("MODIS", families)

        # temp_ch4_k y temp_ch5_k no deben tener nulos
        self.assertEqual(df_clean["temp_ch4_k"].isna().sum(), 0)
        self.assertEqual(df_clean["temp_ch5_k"].isna().sum(), 0)

        # Delta térmico (T4 - T5) debe ser positivo en fuego activo
        self.assertTrue((df_clean["delta_temp_k"] > 0).all())

        # El pixel area debe ser mayor en MODIS que en VIIRS
        modis_area = df_clean[df_clean["sensor_family"] == "MODIS"]["pixel_area_km2"].iloc[0]
        viirs_area = df_clean[df_clean["sensor_family"] == "VIIRS"]["pixel_area_km2"].iloc[0]
        self.assertGreater(modis_area, viirs_area)

    def test_confidence_mapping(self):
        """Verifica que las categorías ('h', 'n', 'l') y los números (0-100) se mapeen correctamente."""
        harmonizer = ModisViirsHarmonizer()

        # VIIRS High
        cat_h, score_h = harmonizer._map_confidence_row("h")
        self.assertEqual(cat_h, "High")
        self.assertEqual(score_h, 0.95)

        # VIIRS Nominal
        cat_n, score_n = harmonizer._map_confidence_row("n")
        self.assertEqual(cat_n, "Nominal")
        self.assertEqual(score_n, 0.65)

        # VIIRS Low
        cat_l, score_l = harmonizer._map_confidence_row("l")
        self.assertEqual(cat_l, "Low")
        self.assertEqual(score_l, 0.30)

        # MODIS numérico alto (85)
        cat_m85, score_m85 = harmonizer._map_confidence_row(85)
        self.assertEqual(cat_m85, "High")
        self.assertEqual(score_m85, 0.85)

        # MODIS numérico nominal (50)
        cat_m50, score_m50 = harmonizer._map_confidence_row(50)
        self.assertEqual(cat_m50, "Nominal")
        self.assertEqual(score_m50, 0.50)

    def test_haversine_clustering_and_codetection(self):
        """Verifica que los 3 puntos cercanos se agrupen y el punto lejano quede aislado (-1)."""
        harmonizer = ModisViirsHarmonizer()
        df_clean = harmonizer.harmonize(self.raw_data)

        clusterer = FireEventClusterer(eps_km=3.0, min_samples=2)
        df_clustered = clusterer.cluster_points(df_clean)
        df_events = clusterer.compute_event_metrics(df_clustered)

        # Verificar asignación de clusters en los puntos
        # Los primeros 3 deben pertenecer al cluster 0
        c0_points = df_clustered.iloc[:3]
        self.assertEqual(len(set(c0_points["cluster_id"])), 1)
        self.assertEqual(c0_points["cluster_id"].iloc[0], 0)

        # El cuarto punto debe ser -1 (aislado)
        self.assertEqual(df_clustered.iloc[3]["cluster_id"], -1)

        # Verificar métricas del evento consolidado
        main_event = df_events[df_events["cluster_numeric_id"] == 0].iloc[0]
        self.assertEqual(main_event["points_count"], 3)
        self.assertEqual(main_event["viirs_count"], 2)
        self.assertEqual(main_event["modis_count"], 1)
        self.assertTrue(main_event["multisensor_confirmed"])
        self.assertAlmostEqual(main_event["frp_total_mw"], 15.6 + 22.0 + 45.2, places=1)

    def test_geojson_export(self):
        """Verifica que el exportador GeoJSON genere un FeatureCollection válido con propiedades cinemáticas enriquecidas y polígonos."""
        harmonizer = ModisViirsHarmonizer()
        df_clean = harmonizer.harmonize(self.raw_data)
        clusterer = FireEventClusterer(eps_km=3.0, min_samples=2)
        df_clustered = clusterer.cluster_points(df_clean)
        df_events = clusterer.compute_event_metrics(df_clustered)

        test_geojson_path = "output/test_output.geojson"
        GeoExporter.export_geojson(df_events, df_clustered, test_geojson_path)

        self.assertTrue(os.path.exists(test_geojson_path))
        import json
        with open(test_geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertGreaterEqual(len(data["features"]), 1)

        # Verificar propiedades enriquecidas para el motor predictivo y la app táctica
        first_feat = data["features"][0]
        self.assertIn("properties", first_feat)
        props = first_feat["properties"]
        self.assertIn("spread_azimuth_deg", props)
        self.assertIn("centroid_lat", props)
        self.assertIn("centroid_lon", props)
        self.assertIn("first_detected", props)
        self.assertIn("last_detected", props)
        self.assertIn("multisensor_confirmed", props)
        self.assertIn("spread_speed_kmh", props)
        self.assertIn("spread_cardinal", props)
        self.assertIn("location_name", props)

        # Verificar que todos los eventos (incluso focos aislados) tengan geometría Polygon
        for feat in data["features"]:
            self.assertEqual(feat["geometry"]["type"], "Polygon")
            self.assertGreaterEqual(len(feat["geometry"]["coordinates"][0]), 3)

        # Limpiar archivo de test
        if os.path.exists(test_geojson_path):
            os.remove(test_geojson_path)

    def test_synthetic_flag_and_physical_metrics(self):
        """Verifica que la bandera is_synthetic, frp_peak_mw y fre_est_mj sean consistentes."""
        ingestor = FIRMSDataIngestor(map_key="test_key")
        df_synth = ingestor.generate_calibrated_fallback(DEFAULT_ARGENTINA_BBOX)
        self.assertTrue((df_synth["is_synthetic"] == True).all())

        harmonizer = ModisViirsHarmonizer()
        df_real_clean = harmonizer.harmonize(self.raw_data)
        self.assertTrue((df_real_clean["is_synthetic"] == False).all())

        clusterer = FireEventClusterer(eps_km=3.0, min_samples=2)
        df_clustered = clusterer.cluster_points(df_real_clean)
        df_events = clusterer.compute_event_metrics(df_clustered)

        main_event = df_events[df_events["cluster_numeric_id"] == 0].iloc[0]
        self.assertIn("frp_peak_mw", main_event)
        self.assertIn("fre_est_mj", main_event)
        self.assertIn("detection_area_ha", main_event)
        self.assertIn("temp_brightness_max_k", main_event)
        self.assertGreater(main_event["frp_peak_mw"], 0.0)
        self.assertGreater(main_event["fre_est_mj"], 0.0)

    def test_dashboard_json_export(self):
        """Verifica que el archivo JSON escalable para el frontend se exporte con todos los KPIs."""
        harmonizer = ModisViirsHarmonizer()
        df_clean = harmonizer.harmonize(self.raw_data)
        clusterer = FireEventClusterer(eps_km=3.0, min_samples=2)
        df_clustered = clusterer.cluster_points(df_clean)
        df_events = clusterer.compute_event_metrics(df_clustered)

        test_json_path = "output/test_dashboard_data.json"
        GeoExporter.export_dashboard_json(
            df_events=df_events,
            df_points=df_clustered,
            area=DEFAULT_ARGENTINA_BBOX,
            day_range=5,
            date_str="2024-09-20",
            json_path=test_json_path
        )

        self.assertTrue(os.path.exists(test_json_path))
        import json
        with open(test_json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.assertIn("metadata", payload)
        self.assertIn("kpis", payload)
        self.assertIn("satellite_breakdown", payload)
        self.assertIn("temporal_series", payload)
        self.assertIn("events", payload)
        self.assertFalse(payload["metadata"]["is_synthetic"])
        self.assertEqual(payload["metadata"]["total_detections"], 4)

        self.assertIn("burning_activity_calendar", payload)
        self.assertIn("cross_sensor_calibration", payload)
        self.assertIn("harmonized_equivalent_detections", payload["kpis"])
        self.assertIn("points", payload)
        self.assertEqual(len(payload["points"]), 4)
        self.assertIn("location_name", payload["events"][0])

        if os.path.exists(test_json_path):
            os.remove(test_json_path)

    def test_cross_sensor_calibration_and_viirs_equivalence(self):
        """Verifica que el factor de equivalencia VIIRS y el cálculo inter-sensor sean consistentes."""
        harmonizer = ModisViirsHarmonizer()
        df_clean = harmonizer.harmonize(self.raw_data)

        # VIIRS debe tener viirs_equiv_count == 1.0
        viirs_rows = df_clean[df_clean["sensor_family"] == "VIIRS"]
        self.assertTrue((viirs_rows["viirs_equiv_count"] == 1.0).all())

        # MODIS debe tener un multiplicador > 1.0 (~4.0x debido al pixel footprint)
        modis_rows = df_clean[df_clean["sensor_family"] == "MODIS"]
        self.assertTrue((modis_rows["viirs_equiv_count"] >= 3.0).all())

        # Calibración cruzada
        calib = harmonizer.compute_cross_sensor_calibration(df_clean)
        self.assertIn("empirical_count_ratio", calib)
        self.assertIn("effective_detection_ratio_literature", calib)
        self.assertEqual(calib["effective_detection_ratio_literature"], 4.0)

    def test_burning_activity_calendar_generation(self):
        """Verifica que el Burning Activity Calendar genere la matriz de 52 semanas y métricas estacionales."""
        harmonizer = ModisViirsHarmonizer()
        df_clean = harmonizer.harmonize(self.raw_data)
        cal = BurningActivityCalendar.compute_calendar(df_clean, DEFAULT_ARGENTINA_BBOX)

        self.assertIn("weeks", cal)
        self.assertIn("months", cal)
        self.assertIn("current_week", cal)
        self.assertIn("seasonal_risk_index", cal)
        self.assertEqual(len(cal["weeks"]), 52)
        self.assertEqual(len(cal["months"]), 12)

        # Verificar que cada semana tenga los campos requeridos
        w1 = cal["weeks"][0]
        self.assertIn("week", w1)
        self.assertIn("baseline_mean", w1)
        self.assertIn("observed_harmonized", w1)
        self.assertIn("z_score", w1)
        self.assertIn("tier", w1)


if __name__ == "__main__":
    unittest.main()
