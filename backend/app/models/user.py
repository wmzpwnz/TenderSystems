"""
Модель пользователя
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    subscription_status = Column(String(20), default="inactive", nullable=False)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    @property
    def has_active_subscription(self) -> bool:
        if self.is_superuser:
            return True
        if self.subscription_status != "active":
            return False
        if self.subscription_expires_at is None:
            return True

        expires_at = self.subscription_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)
