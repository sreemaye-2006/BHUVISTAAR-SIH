"""
BhuVistaar Multi-Format Ingestion Adapters Package.
"""

from app.services.format_adapters.base_adapter import BaseFormatAdapter
from app.services.format_adapters.shapefile_adapter import ShapefileAdapter
from app.services.format_adapters.tabular_adapter import TabularAdapter
from app.services.format_adapters.kml_adapter import KMLAdapter
from app.services.format_adapters.gpkg_adapter import GeoPackageAdapter
from app.services.format_adapters.gpx_adapter import GPXAdapter
from app.services.format_adapters.raster_adapter import RasterAdapter
from app.services.format_adapters.registry import (
    get_adapter_for_extension,
    get_adapter_for_file,
    inspect_file,
    read_vector_data,
)

__all__ = [
    "BaseFormatAdapter",
    "ShapefileAdapter",
    "TabularAdapter",
    "KMLAdapter",
    "GeoPackageAdapter",
    "GPXAdapter",
    "RasterAdapter",
    "get_adapter_for_extension",
    "get_adapter_for_file",
    "inspect_file",
    "read_vector_data",
]
