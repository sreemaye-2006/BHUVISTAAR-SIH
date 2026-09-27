import sqlite3
import json
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from shapely import wkt
import shapely.wkb
from shapely.geometry import mapping

from app.config import settings


import os

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///."):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rel_path = db_url[len("sqlite:///."):]
    if rel_path.startswith("/") or rel_path.startswith("\\"):
        rel_path = rel_path[1:]
    abs_db_path = os.path.join(backend_dir, rel_path)
    db_url = f"sqlite:///{os.path.abspath(abs_db_path).replace(os.sep, '/')}"

engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
    echo=False
)


@event.listens_for(engine, "connect")
def on_sqlite_connect(dbapi_conn, connection_record):
    """Enable GeoAlchemy2 PostGIS/SpatiaLite functions on SQLite connections."""
    if isinstance(dbapi_conn, sqlite3.Connection):
        def GeomFromEWKT(val):
            if val is None:
                return None
            val_str = str(val)
            if ";" in val_str:
                val_str = val_str.split(";", 1)[1]
            geom = wkt.loads(val_str)
            return geom.wkb

        def AsEWKB(val):
            if val is None:
                return None
            if isinstance(val, bytes):
                return val
            geom = wkt.loads(str(val))
            return geom.wkb

        def ST_AsGeoJSON(val):
            if val is None:
                return None
            if isinstance(val, bytes):
                geom = shapely.wkb.loads(val)
            else:
                geom = wkt.loads(str(val))
            return json.dumps(mapping(geom))

        for fn_name in ["GeomFromEWKT", "ST_GeomFromEWKT", "GeomFromText", "ST_GeomFromText"]:
            dbapi_conn.create_function(fn_name, 1, GeomFromEWKT)
        for fn_name in ["AsEWKB", "ST_AsEWKB", "AsBinary", "ST_AsBinary"]:
            dbapi_conn.create_function(fn_name, 1, AsEWKB)
        for fn_name in ["AsGeoJSON", "ST_AsGeoJSON"]:
            dbapi_conn.create_function(fn_name, 1, ST_AsGeoJSON)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()