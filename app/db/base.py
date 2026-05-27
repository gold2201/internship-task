from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    created = Column(DateTime, default=datetime.now(), nullable=False)
    updated = Column(DateTime, default=datetime.now(), onupdate=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
