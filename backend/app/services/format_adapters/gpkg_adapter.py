"""
GeoPackage (.gpkg) vector adapter.
Handles inspection of single and multi-layer GeoPackage files using pyogrio / geopandas.
"""

import os
import geopandas as gpd
import pyogrio

from app.services.format_adapters.base_adapter import BaseFormatAdapter


class GeoPackageAdapter(BaseFormatAdapter):

    def supported_extensions(self) -> list:
        return [".gpkg"]

    def inspect(self, file_path: str, layer: str = None) -> dict:
        file_size = os.path.getsize(file_path)
        try:
            layers_info = pyogrio.list_layers(file_path)
            # list_layers returns array of [layer_name, geometry_type]
            available_layers = [l[0] for l in layers_info] if len(layers_info) > 0 else []
            selected_layer = layer if (layer and layer in available_layers) else (available_layers[0] if available_layers else None)

            if not selected_layer:
                return {
                    "format": "GeoPackage",
                    "dataset_type": "Vector",
                    "crs": None,
                    "geometry_type": None,
                    "feature_count": 0,
                    "file_size": file_size,
                    "columns": [],
                    "bounds": None,
                    "map_ready": False,
                    "ml_ready": False,
                    "extra": {"layers": [], "error": "No layers found in GeoPackage"}
                }

            gdf = gpd.read_file(file_path, layer=selected_layer)
            if gdf.empty:
                return {
                    "format": "GeoPackage",
                    "dataset_type": "Vector",
                    "crs": str(gdf.crs) if gdf.crs else None,
                    "geometry_type": None,
                    "feature_count": 0,
                    "file_size": file_size,
                    "columns": [c for c in gdf.columns if c != gdf.geometry.name],
                    "bounds": None,
                    "map_ready": False,
                    "ml_ready": False,
                    "extra": {"layers": available_layers, "selected_layer": selected_layer}
                }

            geom_types = list(gdf.geometry.geom_type.dropna().unique())
            bounds = gdf.total_bounds.tolist()
            crs_str = str(gdf.crs) if gdf.crs else None
            non_geom_cols = [c for c in gdf.columns if c != gdf.geometry.name]

            return {
                "format": "GeoPackage",
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
                "map_ready": crs_str is not None,
                "ml_ready": crs_str is not None and len(gdf) > 0,
                "extra": {
                    "layers": available_layers,
                    "selected_layer": selected_layer,
                    "geometry_types": geom_types
                }
            }

        except Exception as e:
            return {
                "format": "GeoPackage",
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
        layer = kwargs.get("layer")
        if not layer:
            layers_info = pyogrio.list_layers(file_path)
            if len(layers_info) > 0:
                layer = layers_info[0][0]
        gdf = gpd.read_file(file_path, layer=layer)
        if gdf.empty:
            raise ValueError(f"GeoPackage layer '{layer}' contains no features.")
        return gdf
