"""
KML / KMZ adapter.
Reads KML geometry and attributes via geopandas (which uses pyogrio/fiona/GDAL under the hood).
KMZ is a zipped KML — extracted before reading.
"""

import os
import zipfile
import tempfile
import shutil
import geopandas as gpd

from app.services.format_adapters.base_adapter import BaseFormatAdapter


class KMLAdapter(BaseFormatAdapter):

    def supported_extensions(self) -> list:
        return [".kml", ".kmz"]

    def inspect(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        fmt = "KMZ" if ext == ".kmz" else "KML"
        tmp_dir = None

        try:
            kml_path = file_path
            if ext == ".kmz":
                tmp_dir = tempfile.mkdtemp(prefix="bhv_kmz_")
                with zipfile.ZipFile(file_path, "r") as zf:
                    # KMZ contains exactly one doc.kml (or similar)
                    kml_members = [m for m in zf.namelist() if m.lower().endswith(".kml")]
                    if not kml_members:
                        return self._error_result(fmt, file_size, "KMZ contains no .kml file")
                    zf.extract(kml_members[0], tmp_dir)
                    kml_path = os.path.join(tmp_dir, kml_members[0])

            gdf = gpd.read_file(kml_path)

            if gdf.empty:
                return {
                    "format": fmt,
                    "dataset_type": "Vector",
                    "crs": str(gdf.crs) if gdf.crs else "EPSG:4326",
                    "geometry_type": None,
                    "feature_count": 0,
                    "file_size": file_size,
                    "columns": [],
                    "bounds": None,
                    "map_ready": False,
                    "ml_ready": False,
                    "extra": {"note": "KML is empty"}
                }

            geom_types = list(gdf.geometry.geom_type.dropna().unique())
            bounds = gdf.total_bounds.tolist()
            non_geom_cols = [c for c in gdf.columns if c != gdf.geometry.name]
            crs_str = str(gdf.crs) if gdf.crs else "EPSG:4326"

            return {
                "format": fmt,
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
            return self._error_result(fmt, file_size, str(e))
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _error_result(self, fmt, file_size, error):
        return {
            "format": fmt,
            "dataset_type": "Unknown",
            "crs": None,
            "geometry_type": None,
            "feature_count": None,
            "file_size": file_size,
            "columns": [],
            "bounds": None,
            "map_ready": False,
            "ml_ready": False,
            "extra": {"error": error}
        }

    def read_as_geodataframe(self, file_path: str, **kwargs) -> gpd.GeoDataFrame:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".kmz":
            upload_dir = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            extract_target = os.path.join(upload_dir, f"_extracted_{base_name}")
            os.makedirs(extract_target, exist_ok=True)
            with zipfile.ZipFile(file_path, "r") as zf:
                kml_members = [m for m in zf.namelist() if m.lower().endswith(".kml")]
                if not kml_members:
                    raise ValueError("KMZ contains no .kml file")
                target_kml = os.path.join(extract_target, kml_members[0])
                zf.extract(kml_members[0], extract_target)
                gdf = gpd.read_file(target_kml)
        else:
            gdf = gpd.read_file(file_path)

        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        return gdf

