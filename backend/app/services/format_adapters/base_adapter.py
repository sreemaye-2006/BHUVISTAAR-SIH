"""Base adapter interface for BhuVistaar multi-format ingestion."""

from abc import ABC, abstractmethod


class BaseFormatAdapter(ABC):
    """Abstract base class all format-specific adapters must implement."""

    @abstractmethod
    def inspect(self, file_path: str) -> dict:
        """
        Perform lightweight pre-import inspection without committing anything.
        Returns metadata dict with at minimum:
          {
            "format": str,
            "dataset_type": str,       # Vector | Raster | Tabular | Image
            "crs": str | None,
            "geometry_type": str | None,
            "feature_count": int | None,
            "file_size": int,
            "columns": list,
            "bounds": dict | None,
            "map_ready": bool,
            "ml_ready": bool,
            "extra": dict              # adapter-specific metadata
          }
        """
        raise NotImplementedError

    @abstractmethod
    def supported_extensions(self) -> list:
        """Return list of lowercase extensions this adapter handles, e.g. ['.csv', '.xlsx']."""
        raise NotImplementedError

    def read_as_geodataframe(self, file_path: str, **kwargs):
        """
        Convert/read the file into a geopandas.GeoDataFrame for vector processing.
        For raster formats, raises NotImplementedError.
        """
        raise NotImplementedError("This format does not support direct vector GeoDataFrame conversion.")
