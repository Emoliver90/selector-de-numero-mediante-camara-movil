"""Configuración de la base de datos (SQLite + SQLAlchemy)."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

os.makedirs("database", exist_ok=True)

engine = create_engine(
    "sqlite:///database/ruletas.db",
    connect_args={"check_same_thread": False},
)
Session = sessionmaker(bind=engine)
Base = declarative_base()


def nueva_sesion():
    """Devuelve una sesión nueva de SQLAlchemy (una por operación)."""
    return Session()
