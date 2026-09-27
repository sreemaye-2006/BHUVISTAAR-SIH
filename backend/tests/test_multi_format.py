import os
import tempfile
import json
import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from app.services.file_validation import validate_file_extension, get_file_type
from app.services.format_adapters import (
    get_adapter_for_extension,
    get_adapter_for_file,
    inspect_file,
    read_vector_data,
    ShapefileAdapter,
    TabularAdapter,
    KMLAdapter,
    GeoPackageAdapter,
    GPXAdapter,
    RasterAdapter,
)


def test_allowed_extensions_and_types():
    assert validate_file_extension("survey.geojson") is True
    assert validate_file_extension("boundary.shp") is True
    assert validate_file_extension("parcels.gpkg") is True
    assert validate_file_extension("waypoints.gpx") is True
    assert validate_file_extension("ledger.csv") is True
    assert validate_file_extension("records.xlsx") is True
    assert validate_file_extension("records.xls") is True
    assert validate_file_extension("aerial.tif") is True
    assert validate_file_extension("satellite.png") is True
    assert validate_file_extension("photo.jpg") is True
    assert validate_file_extension("archive.zip") is True
    assert validate_file_extension("malicious.exe") is False

    assert get_file_type("a.gpx") == "GPX"
    assert get_file_type("a.xlsx") == "Excel"
    assert get_file_type("a.png") == "Raster/Image"


def test_adapter_registry_lookup():
    assert get_adapter_for_extension(".geojson") is not None
    assert get_adapter_for_extension(".shp") is not None
    assert get_adapter_for_extension(".zip") is not None
    assert get_adapter_for_extension(".csv") is not None
    assert get_adapter_for_extension(".xlsx") is not None
    assert get_adapter_for_extension(".kml") is not None
    assert get_adapter_for_extension(".kmz") is not None
    assert get_adapter_for_extension(".gpkg") is not None
    assert get_adapter_for_extension(".gpx") is not None
    assert get_adapter_for_extension(".tif") is not None
    assert get_adapter_for_extension(".jpg") is not None
    assert get_adapter_for_extension(".png") is not None
    assert get_adapter_for_extension(".unknown") is None


def test_geojson_adapter():
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [77.5946, 12.9716]},
                "properties": {"name": "Bengaluru Survey Mark", "code": "BLR_01"}
            }
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".geojson", mode="w", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        meta = inspect_file(temp_path)
        assert meta["format"] == "GeoJSON"
        assert meta["dataset_type"] == "Vector"
        assert meta["feature_count"] == 1
        assert "name" in meta["columns"]

        gdf = read_vector_data(temp_path)
        assert len(gdf) == 1
        assert gdf.iloc[0]["name"] == "Bengaluru Survey Mark"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_tabular_csv_adapter_with_coordinates():
    df = pd.DataFrame([
        {"parcel_id": "P101", "latitude": 13.0827, "longitude": 80.2707, "owner": "Govt Land"},
        {"parcel_id": "P102", "latitude": 13.0850, "longitude": 80.2750, "owner": "Private Parcel"}
    ])
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        df.to_csv(f.name, index=False)
        temp_path = f.name

    try:
        meta = inspect_file(temp_path)
        assert meta["format"] == "CSV"
        assert meta["dataset_type"] == "Vector"
        assert meta["feature_count"] == 2
        assert meta["map_ready"] is True
        assert meta["extra"]["coords_detected"] is True

        gdf = read_vector_data(temp_path)
        assert len(gdf) == 2
        assert isinstance(gdf.geometry.iloc[0], Point)
        assert gdf.crs.to_string() == "EPSG:4326"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_gpx_adapter():
    gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="BhuVistaar Rover" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="12.9716" lon="77.5946">
    <name>GCP_Benchmark_1</name>
    <ele>920.5</ele>
  </wpt>
  <trk>
    <name>Boundary_Perimeter_Survey</name>
    <trkseg>
      <trkpt lat="12.9710" lon="77.5940"></trkpt>
      <trkpt lat="12.9720" lon="77.5950"></trkpt>
    </trkseg>
  </trk>
</gpx>"""
    with tempfile.NamedTemporaryFile(suffix=".gpx", mode="w", delete=False) as f:
        f.write(gpx_content)
        temp_path = f.name

    try:
        meta = inspect_file(temp_path)
        assert meta["format"] == "GPX"
        assert meta["dataset_type"] == "Vector"
        assert meta["feature_count"] == 2
        assert meta["map_ready"] is True

        gdf = read_vector_data(temp_path)
        assert len(gdf) == 2
        assert "waypoint" in gdf["feature_type"].values
        assert "track" in gdf["feature_type"].values
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
