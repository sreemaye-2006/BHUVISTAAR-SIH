"""
Shapefile adapter — handles .shp direct files and ZIP archives.

ZIP contents are safely extracted to a temporary directory with:
  - Path traversal protection
  - Required component validation (.shp, .shx, .dbf)
  - Cleanup after inspection
"""

import os
import zipfile
import tempfile
import shutil
import geopandas as gpd

from app.services.format_adapters.base_adapter import BaseFormatAdapter


REQUIRED_SHP_COMPONENTS = {".shp", ".shx", ".dbf"}
OPTIONAL_SHP_COMPONENTS = {".prj", ".cpg", ".sbn", ".sbx"}


def _safe_extract_zip(zip_path: str, extract_to: str) -> list:
    """
    Extract a ZIP safely, guarding against path traversal.
    Returns list of extracted absolute file paths.
    """
    extracted = []
    abs_dest = os.path.realpath(extract_to)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # Strip leading slashes / absolute paths
            member_name = member.filename.lstrip("/").lstrip("\\")
            # Guard against path traversal
            target_path = os.path.realpath(os.path.join(abs_dest, member_name))
            if not target_path.startswith(abs_dest + os.sep) and target_path != abs_dest:
                raise ValueError(f"Path traversal detected in ZIP: {member.filename}")
            zf.extract(member, path=abs_dest)
            if not member.is_dir():
                extracted.append(target_path)

    return extracted


class ShapefileAdapter(BaseFormatAdapter):

    def supported_extensions(self) -> list:
        return [".shp", ".zip"]

    def inspect(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        tmp_dir = None

        try:
            if ext == ".zip":
                tmp_dir = tempfile.mkdtemp(prefix="bhv_shp_")
                extracted = _safe_extract_zip(file_path, tmp_dir)

                # Find the .shp file
                shp_files = [f for f in extracted if f.lower().endswith(".shp")]
                if not shp_files:
                    return {
                        "format": "Shapefile",
                        "dataset_type": "Unknown",
                        "crs": None,
                        "geometry_type": None,
                        "feature_count": None,
                        "file_size": file_size,
                        "columns": [],
                        "bounds": None,
                        "map_ready": False,
                        "ml_ready": False,
                        "extra": {
                            "error": "Shapefile ZIP is missing required components (.shp, .shx, .dbf)"
                        }
                    }

                shp_path = shp_files[0]

                # Check required components relative to the .shp
                base_dir = os.path.dirname(shp_path)
                base_name = os.path.splitext(os.path.basename(shp_path))[0]
                present = {
                    os.path.splitext(f)[1].lower()
                    for f in os.listdir(base_dir)
                    if os.path.splitext(f)[0] == base_name
                }
                missing = REQUIRED_SHP_COMPONENTS - present
                if missing:
                    return {
                        "format": "Shapefile",
                        "dataset_type": "Unknown",
                        "crs": None,
                        "geometry_type": None,
                        "feature_count": None,
                        "file_size": file_size,
                        "columns": [],
                        "bounds": None,
                        "map_ready": False,
                        "ml_ready": False,
                        "extra": {
                            "error": f"Shapefile missing: {', '.join(sorted(missing))}"
                        }
                    }

                return self._read_shp(shp_path, file_size)

            else:
                # Direct .shp file — read directly
                return self._read_shp(file_path, file_size)

        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _read_shp(self, shp_path: str, file_size: int) -> dict:
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            return {
                "format": "Shapefile",
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

        if gdf.empty:
            has_crs = gdf.crs is not None
            return {
                "format": "Shapefile",
                "dataset_type": "Vector",
                "crs": str(gdf.crs) if gdf.crs else None,
                "geometry_type": None,
                "feature_count": 0,
                "file_size": file_size,
                "columns": [c for c in gdf.columns if c != gdf.geometry.name],
                "bounds": None,
                "map_ready": False,
                "ml_ready": False,
                "extra": {"note": "Empty dataset"}
            }

        geom_types = list(gdf.geometry.geom_type.dropna().unique())
        bounds = gdf.total_bounds.tolist()
        crs_str = str(gdf.crs) if gdf.crs else None
        has_crs = gdf.crs is not None
        non_geom_cols = [c for c in gdf.columns if c != gdf.geometry.name]

        return {
            "format": "Shapefile",
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
            "map_ready": has_crs,
            "ml_ready": has_crs and len(gdf) > 0,
            "extra": {
                "geometry_types": geom_types,
                "attribute_count": len(non_geom_cols)
            }
        }

    def read_as_geodataframe(self, file_path: str, **kwargs) -> gpd.GeoDataFrame:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".zip":
            # Extract to a persistent or temp extraction directory for processing
            upload_dir = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            extract_target = os.path.join(upload_dir, f"_extracted_{base_name}")
            os.makedirs(extract_target, exist_ok=True)
            extracted = _safe_extract_zip(file_path, extract_target)
            shp_files = [f for f in extracted if f.lower().endswith(".shp")]
            if not shp_files:
                raise ValueError("Shapefile ZIP contains no .shp file")
            return gpd.read_file(shp_files[0])
        else:
            return gpd.read_file(file_path)
