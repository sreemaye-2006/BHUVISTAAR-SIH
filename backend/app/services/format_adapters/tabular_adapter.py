"""
Tabular adapter — handles CSV and Excel (.xlsx, .xls) files.

For CSV/Excel:
  1. Reads with pandas
  2. Detects coordinate columns by name patterns
  3. If coordinates exist → builds Point GeoDataFrame → Vector/Tabular-Spatial
  4. If no coordinates   → Attribute-only dataset (no fake geometry created)

No geometry is ever invented if coordinates are not present.
"""

import os
import re

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from app.services.format_adapters.base_adapter import BaseFormatAdapter


# Regex patterns for coordinate column detection (case-insensitive)
LAT_PATTERNS = re.compile(r"^(lat(itude)?|y)$", re.IGNORECASE)
LON_PATTERNS = re.compile(r"^(lon(g(itude)?)?|lng|x)$", re.IGNORECASE)


def _detect_coord_columns(columns):
    """Return (lat_col, lon_col) or (None, None)."""
    lat_col = None
    lon_col = None
    for col in columns:
        if LAT_PATTERNS.match(col.strip()):
            lat_col = col
        if LON_PATTERNS.match(col.strip()):
            lon_col = col
    return lat_col, lon_col


def _read_dataframe(file_path: str, sheet_name=None):
    """Read CSV or Excel into a pandas DataFrame."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path, nrows=50000), None, None
    elif ext in (".xlsx", ".xls"):
        xf = pd.ExcelFile(file_path)
        sheets = xf.sheet_names
        chosen = sheet_name if sheet_name in sheets else sheets[0]
        df = pd.read_excel(file_path, sheet_name=chosen)
        return df, sheets, chosen
    else:
        raise ValueError(f"Unsupported tabular format: {ext}")


class TabularAdapter(BaseFormatAdapter):

    def supported_extensions(self) -> list:
        return [".csv", ".xlsx", ".xls"]

    def inspect(self, file_path: str, sheet_name: str = None) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        fmt = "CSV" if ext == ".csv" else ("Excel XLSX" if ext == ".xlsx" else "Excel XLS")

        try:
            df, sheets, chosen_sheet = _read_dataframe(file_path, sheet_name)
        except Exception as e:
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
                "extra": {"error": str(e)}
            }

        if df is None or df.empty:
            return {
                "format": fmt,
                "dataset_type": "Tabular",
                "crs": None,
                "geometry_type": None,
                "feature_count": 0,
                "file_size": file_size,
                "columns": list(df.columns) if df is not None else [],
                "bounds": None,
                "map_ready": False,
                "ml_ready": False,
                "extra": {"sheets": sheets, "selected_sheet": chosen_sheet}
            }

        columns = list(df.columns)
        lat_col, lon_col = _detect_coord_columns(columns)
        has_coords = lat_col is not None and lon_col is not None

        extra = {
            "sheets": sheets,
            "selected_sheet": chosen_sheet,
            "row_count": len(df),
            "column_count": len(columns),
        }

        if has_coords:
            # Try building geometry for bounds
            try:
                valid = df[[lat_col, lon_col]].dropna()
                valid[lat_col] = pd.to_numeric(valid[lat_col], errors="coerce")
                valid[lon_col] = pd.to_numeric(valid[lon_col], errors="coerce")
                valid = valid.dropna()
                if not valid.empty:
                    bounds = {
                        "min_x": float(valid[lon_col].min()),
                        "min_y": float(valid[lat_col].min()),
                        "max_x": float(valid[lon_col].max()),
                        "max_y": float(valid[lat_col].max()),
                    }
                else:
                    bounds = None
            except Exception:
                bounds = None

            extra["lat_col"] = lat_col
            extra["lon_col"] = lon_col
            extra["coords_detected"] = True

            return {
                "format": fmt,
                "dataset_type": "Vector",          # Tabular with spatial
                "crs": "EPSG:4326",                 # Assumed WGS84 for lat/lon
                "geometry_type": "Point",
                "feature_count": len(df),
                "file_size": file_size,
                "columns": columns,
                "bounds": bounds,
                "map_ready": True,
                "ml_ready": True,
                "extra": extra
            }
        else:
            # Attribute-only — no fake geometry
            extra["coords_detected"] = False
            return {
                "format": fmt,
                "dataset_type": "Tabular",
                "crs": None,
                "geometry_type": None,
                "feature_count": len(df),
                "file_size": file_size,
                "columns": columns,
                "bounds": None,
                "map_ready": False,
                "ml_ready": False,
                "extra": extra
            }

    def to_geodataframe(self, file_path: str, sheet_name: str = None, lat_col: str = None, lon_col: str = None, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
        """
        Build a GeoDataFrame from a tabular file with coordinate columns.
        Returns None if no coordinates are found (no fake geometry).
        """
        df, _, _ = _read_dataframe(file_path, sheet_name)
        if not lat_col or not lon_col:
            detected_lat, detected_lon = _detect_coord_columns(list(df.columns))
            lat_col = lat_col or detected_lat
            lon_col = lon_col or detected_lon

        if lat_col is None or lon_col is None:
            return None

        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        df = df.dropna(subset=[lat_col, lon_col])

        geometry = [Point(row[lon_col], row[lat_col]) for _, row in df.iterrows()]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs or "EPSG:4326")
        return gdf

    def read_as_geodataframe(self, file_path: str, **kwargs) -> gpd.GeoDataFrame:
        sheet_name = kwargs.get("sheet_name")
        lat_col = kwargs.get("lat_col")
        lon_col = kwargs.get("lon_col")
        crs = kwargs.get("crs", "EPSG:4326")
        gdf = self.to_geodataframe(file_path, sheet_name=sheet_name, lat_col=lat_col, lon_col=lon_col, crs=crs)
        if gdf is None or gdf.empty:
            raise ValueError("Tabular dataset does not have detected coordinate columns (latitude/longitude).")
        return gdf

