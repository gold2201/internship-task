from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.orm import declarative_base

from app.models.db_models import Transaction, User, UserBalance  # noqa

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
