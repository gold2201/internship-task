import uuid
from datetime import datetime

import uuid6
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from ulid import ULID

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class User(BaseModel):
    __tablename__ = "user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=True, unique=True)
    status = Column(String, nullable=True)

    user_balance = relationship("UserBalance", back_populates="owner")
    transactions = relationship("Transaction", back_populates="user")


class UserBalance(BaseModel):
    __tablename__ = "user_balance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    currency = Column(String, nullable=True)
    amount = Column(Numeric, nullable=True)
    UniqueConstraint("user_id", "currency", name="user_balance_user_currency_unique")

    owner = relationship("User", back_populates="user_balance")


class Transaction(BaseModel):
    __tablename__ = "transaction"
    id = Column(String(26), primary_key=True, default=lambda: str(ULID()))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    currency = Column(String, nullable=True)
    amount = Column(Numeric, nullable=True)
    status = Column(String, nullable=True)

    user = relationship("User", back_populates="transactions")
