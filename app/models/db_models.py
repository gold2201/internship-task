import uuid
from datetime import datetime

import uuid6
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ulid import ULID

from app.db.base import BaseModel


class User(BaseModel):
    __tablename__ = "user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=True, unique=True)
    status = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_superuser = Column(Boolean, nullable=False, default=False)

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


class RefreshToken(BaseModel):
    __tablename__ = "refresh_token"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(Text, nullable=False, unique=True, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(DateTime(timezone=True), nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), default=datetime.now(), nullable=False)
