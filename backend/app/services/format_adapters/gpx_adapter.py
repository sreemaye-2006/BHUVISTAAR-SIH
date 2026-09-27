"""
GPX (GPS Exchange Format) vector adapter.
Parses GPX waypoints, tracks, and routes into a GeoPandas GeoDataFrame using standard xml.etree.
"""

import os
import xml.etree.ElementTree as ET
import geopandas as gpd
from shapely.geometry import Point, LineString

from app.services.format_adapters.base_adapter import BaseFormatAdapter


class GPXAdapter(BaseFormatAdapter):

    def supported_extensions(self) -> list:
        return [".gpx"]

    def _parse_gpx(self, file_path: str) -> gpd.GeoDataFrame:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Handle GPX namespaces dynamically (e.g. {http://www.topografix.com/GPX/1/1})
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        records = []
        geometries = []

        # 1. Parse Waypoints (<wpt>)
        for wpt in root.findall(f"{ns}wpt"):
            try:
                lat = float(wpt.attrib["lat"])
                lon = float(wpt.attrib["lon"])
                geom = Point(lon, lat)

                name_el = wpt.find(f"{ns}name")
                ele_el = wpt.find(f"{ns}ele")
                time_el = wpt.find(f"{ns}time")
                desc_el = wpt.find(f"{ns}desc")

                records.append({
                    "feature_type": "waypoint",
                    "name": name_el.text if name_el is not None else None,
                    "elevation": float(ele_el.text) if ele_el is not None and ele_el.text else None,
                    "time": time_el.text if time_el is not None else None,
                    "description": desc_el.text if desc_el is not None else None,
                })
                geometries.append(geom)
            except Exception:
                continue

        # 2. Parse Tracks (<trk>)
        for trk_idx, trk in enumerate(root.findall(f"{ns}trk")):
            trk_name_el = trk.find(f"{ns}name")
            trk_name = trk_name_el.text if trk_name_el is not None else f"Track_{trk_idx + 1}"

            for seg_idx, trkseg in enumerate(trk.findall(f"{ns}trkseg")):
                coords = []
                for pt in trkseg.findall(f"{ns}trkpt"):
                    try:
                        coords.append((float(pt.attrib["lon"]), float(pt.attrib["lat"])))
                    except Exception:
                        continue

                if len(coords) >= 2:
                    geometries.append(LineString(coords))
                    records.append({
                        "feature_type": "track",
                        "name": f"{trk_name}_seg_{seg_idx + 1}",
                        "elevation": None,
                        "time": None,
                        "description": f"Track segment with {len(coords)} points",
                    })
                elif len(coords) == 1:
                    geometries.append(Point(coords[0]))
                    records.append({
                        "feature_type": "track_point",
                        "name": f"{trk_name}_pt",
                        "elevation": None,
                        "time": None,
                        "description": "Single track point",
                    })

        # 3. Parse Routes (<rte>)
        for rte_idx, rte in enumerate(root.findall(f"{ns}rte")):
            rte_name_el = rte.find(f"{ns}name")
            rte_name = rte_name_el.text if rte_name_el is not None else f"Route_{rte_idx + 1}"
            coords = []
            for pt in rte.findall(f"{ns}rtept"):
                try:
                    coords.append((float(pt.attrib["lon"]), float(pt.attrib["lat"])))
                except Exception:
                    continue
            if len(coords) >= 2:
                geometries.append(LineString(coords))
                records.append({
                    "feature_type": "route",
                    "name": rte_name,
                    "elevation": None,
                    "time": None,
                    "description": f"Route with {len(coords)} points",
                })

        if not geometries:
            return gpd.GeoDataFrame([], columns=["feature_type", "name", "elevation", "time", "description"], geometry=[], crs="EPSG:4326")

        import pandas as pd
        df = pd.DataFrame(records)
        gdf = gpd.GeoDataFrame(df, geometry=geometries, crs="EPSG:4326")
        return gdf

    def inspect(self, file_path: str) -> dict:
        file_size = os.path.getsize(file_path)
        try:
            gdf = self._parse_gpx(file_path)
            if gdf.empty:
                return {
                    "format": "GPX",
                    "dataset_type": "Vector",
                    "crs": "EPSG:4326",
                    "geometry_type": None,
                    "feature_count": 0,
                    "file_size": file_size,
                    "columns": [],
                    "bounds": None,
                    "map_ready": False,
                    "ml_ready": False,
                    "extra": {"note": "GPX file contains no coordinates"}
                }

            geom_types = list(gdf.geometry.geom_type.dropna().unique())
            bounds = gdf.total_bounds.tolist()
            non_geom_cols = [c for c in gdf.columns if c != gdf.geometry.name]

            return {
                "format": "GPX",
                "dataset_type": "Vector",
                "crs": "EPSG:4326",
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
                "extra": {
                    "geometry_types": geom_types,
                    "feature_types": list(gdf["feature_type"].unique()) if "feature_type" in gdf else []
                }
            }
        except Exception as e:
            return {
                "format": "GPX",
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
        gdf = self._parse_gpx(file_path)
        if gdf.empty:
            raise ValueError("GPX file contains no valid points, tracks, or routes.")
        return gdf
