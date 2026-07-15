"""
Shared declarative base for all SQLAlchemy ORM models.

All models must import Base from this module — never from database.py directly —
to avoid circular imports and to keep the ORM model graph self-contained.
"""

from app.core.database import Base

__all__ = ["Base"]
