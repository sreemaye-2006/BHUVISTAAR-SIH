"""
Central registry and dispatcher for multi-format dataset adapters in BhuVistaar.
"""

import os
from typing import Optional, Dict
import geopandas as gpd

from app.services.format_adapters.base_adapter import BaseFormatAdapter
from app.services.format_adapters.shapefile_adapter import ShapefileAdapter
from app.services.format_adapters.tabular_adapter import TabularAdapter
from app.services.format_adapters.kml_adapter import KMLAdapter
from app.services.format_adapters.gpkg_adapter import GeoPackageAdapter
from app.services.format_adapters.gpx_adapter import GPXAdapter
from app.services.format_adapters.raster_adapter import RasterAdapter


class GeoJsonAdapter(BaseFormatAdapter):
    """Native GeoJSON / JSON adapter using GeoPandas."""

    def supported_extensions(self) -> list:
        return [".geojson", ".json"]

    def inspect(self, file_path: str) -> dict:
        file_size = os.path.getsize(file_path)
        try:
            gdf = gpd.read_file(file_path)
            if gdf.empty:
                return {
                    "format": "GeoJSON",
                    "dataset_type": "Vector",
                    "crs": str(gdf.crs) if gdf.crs else None,
                    "geometry_type": None,
                    "feature_count": 0,
                    "file_size": file_size,
                    "columns": [],
                    "bounds": None,
                    "map_ready": False,
                    "ml_ready": False,
                    "extra": {"note": "Empty GeoJSON"}
                }
            geom_types = list(gdf.geometry.geom_type.dropna().unique())
            bounds = gdf.total_bounds.tolist()
            crs_str = str(gdf.crs) if gdf.crs else "EPSG:4326"
            non_geom_cols = [c for c in gdf.columns if c != gdf.geometry.name]

            return {
                "format": "GeoJSON",
                "dataset_type": "Vector",
                "crs": crs_str,
                "geometry_type": ", ".join(geom_types),
                "feature_count": len(gdf),
                "file_size": file_size,
                "columns": non_geom_cols,
                "bounds": {
                    "min_x": bounds[0], "min_y": bounds[1],
                    "max_x": bounds[2], "max_y": bounds[3]
                },
                "map_ready": True,
                "ml_ready": len(gdf) > 0,
                "extra": {"geometry_types": geom_types}
            }
        except Exception as e:
            return {
                "format": "GeoJSON",
                "dataset_type": "Unknown",
                "crs": None,
                "geometry_type": None,
                "feature_count": None,
                "file_size": file_size,
                "columns": [],
                "bounds": None,
                "map_ready": False,
                "ml_ready": False,
                "extra": {"error": str(e)}
            }

    def read_as_geodataframe(self, file_path: str, **kwargs) -> gpd.GeoDataFrame:
        gdf = gpd.read_file(file_path)
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        return gdf


# Instantiate singleton adapters
_ADAPTER_INSTANCES = [
    GeoJsonAdapter(),
    ShapefileAdapter(),
    TabularAdapter(),
    KMLAdapter(),
    GeoPackageAdapter(),
    GPXAdapter(),
    RasterAdapter(),
]

_EXTENSION_MAP: Dict[str, BaseFormatAdapter] = {}
for adapter in _ADAPTER_INSTANCES:
    for ext in adapter.supported_extensions():
        _EXTENSION_MAP[ext.lower()] = adapter


def get_adapter_for_extension(extension: str) -> Optional[BaseFormatAdapter]:
    """Retrieve adapter by file extension (with or without leading dot)."""
    if not extension.startswith("."):
        extension = "." + extension
    return _EXTENSION_MAP.get(extension.lower())


def get_adapter_for_file(file_path: str) -> Optional[BaseFormatAdapter]:
    """Retrieve adapter by inspecting file path extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return get_adapter_for_extension(ext)


def inspect_file(file_path: str, **kwargs) -> dict:
    """Inspect any supported file and return standardized metadata."""
    adapter = get_adapter_for_file(file_path)
    if not adapter:
        raise ValueError(f"No adapter available for file: {file_path}")
    return adapter.inspect(file_path, **kwargs)


def read_vector_data(file_path: str, **kwargs) -> gpd.GeoDataFrame:
    """Read any vector file through its format adapter into a standard GeoDataFrame."""
    adapter = get_adapter_for_file(file_path)
    if not adapter:
        raise ValueError(f"No adapter available for vector format: {file_path}")
    return adapter.read_as_geodataframe(file_path, **kwargs)
