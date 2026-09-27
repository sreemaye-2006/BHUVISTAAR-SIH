"""
Raster and Imagery Adapter for GeoTIFF (.tif, .tiff) and standard images (.jpg, .jpeg, .png).
Integrates with rasterio and PIL for metadata inspection.
"""

import os
from PIL import Image
from app.services.format_adapters.base_adapter import BaseFormatAdapter


def _extract_exif_gps(img):
    """Extract GPS coordinates from EXIF metadata if present. Returns dict or None."""
    try:
        exif = img.getexif()
        if not exif:
            return None
        gps_info = exif.get_ifd(0x8825)
        if not gps_info:
            return None

        def _to_float(v):
            if isinstance(v, (tuple, list)):
                return float(v[0]) / float(v[1]) if len(v) > 1 and v[1] != 0 else float(v[0])
            return float(v)

        lat = gps_info.get(2)
        lat_ref = gps_info.get(1, "N")
        lon = gps_info.get(4)
        lon_ref = gps_info.get(3, "E")

        if lat and lon and len(lat) >= 3 and len(lon) >= 3:
            lat_deg = _to_float(lat[0]) + _to_float(lat[1]) / 60.0 + _to_float(lat[2]) / 3600.0
            if str(lat_ref).upper() == "S":
                lat_deg = -lat_deg
            lon_deg = _to_float(lon[0]) + _to_float(lon[1]) / 60.0 + _to_float(lon[2]) / 3600.0
            if str(lon_ref).upper() == "W":
                lon_deg = -lon_deg
            return {"latitude": round(lat_deg, 6), "longitude": round(lon_deg, 6)}
    except Exception:
        pass
    return None


class RasterAdapter(BaseFormatAdapter):

    def supported_extensions(self) -> list:
        return [".tif", ".tiff", ".jpg", ".jpeg", ".png"]

    def inspect(self, file_path: str) -> dict:
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        is_tiff = ext in (".tif", ".tiff")

        if is_tiff:
            try:
                import rasterio
                with rasterio.open(file_path) as src:
                    crs_str = str(src.crs) if src.crs else None
                    bounds = src.bounds
                    return {
                        "format": "GeoTIFF" if crs_str else "TIFF",
                        "dataset_type": "Raster",
                        "crs": crs_str,
                        "geometry_type": "Raster Grid",
                        "feature_count": src.count,  # number of bands
                        "file_size": file_size,
                        "columns": [f"Band_{i}" for i in range(1, src.count + 1)],
                        "bounds": {
                            "min_x": float(bounds.left),
                            "min_y": float(bounds.bottom),
                            "max_x": float(bounds.right),
                            "max_y": float(bounds.top),
                        } if crs_str else None,
                        "map_ready": crs_str is not None,
                        "ml_ready": crs_str is not None,
                        "extra": {
                            "width": src.width,
                            "height": src.height,
                            "band_count": src.count,
                            "driver": src.driver,
                            "dtypes": [str(d) for d in src.dtypes],
                            "nodata": src.nodata,
                            "is_georeferenced": crs_str is not None,
                            "georeferencing_action": "Ready for GIS" if crs_str else "GCP Ground Control Georeferencing required"
                        }
                    }
            except Exception:
                pass  # Fallback to PIL below

        # Generic Image (or non-geotiff / failed tiff fallback)
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode
                format_name = img.format or ext.lstrip(".").upper()
                gps = _extract_exif_gps(img)
                is_georef = gps is not None
                crs = "EPSG:4326" if is_georef else None

                return {
                    "format": format_name,
                    "dataset_type": "Drone / Survey Image" if is_georef else "Image Asset",
                    "crs": crs,
                    "geometry_type": "Point (EXIF GPS)" if is_georef else None,
                    "feature_count": 1 if is_georef else (len(img.getbands()) if hasattr(img, "getbands") else 1),
                    "file_size": file_size,
                    "columns": list(img.getbands()) if hasattr(img, "getbands") else ["Band_1"],
                    "bounds": {
                        "min_x": gps["longitude"],
                        "min_y": gps["latitude"],
                        "max_x": gps["longitude"],
                        "max_y": gps["latitude"],
                    } if is_georef else None,
                    "map_ready": is_georef,
                    "ml_ready": is_georef,
                    "extra": {
                        "width": width,
                        "height": height,
                        "mode": mode,
                        "exif_gps": gps,
                        "is_georeferenced": is_georef,
                        "georeferencing_action": (
                            "Georeferenced via EXIF GPS coordinates."
                            if is_georef
                            else "No GPS metadata found. Image treated as survey image asset."
                        )
                    }
                }
        except Exception as e:
            return {
                "format": ext.lstrip(".").upper(),
                "dataset_type": "Raster/Imagery",
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

    def read_as_geodataframe(self, file_path: str, **kwargs):
        raise NotImplementedError(
            "Raster datasets are processed via the BhuVistaar Raster / Georeferencing pipeline, not vector tables."
        )
