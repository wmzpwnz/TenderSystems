from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class SearchSubscription(Base):
    """
    Модель для подписок на поиск.
    Пользователь сохраняет набор фильтров, и система периодически проверяет новые тендеры по ним.
    """
    __tablename__ = "search_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    
    name = Column(String(255), nullable=False)
    
    # JSON объект с фильтрами (TenderFilter)
    filters = Column(JSON, nullable=False)
    
    # Режим уведомлений
    notify_email = Column(Boolean, default=True)
    notify_telegram = Column(Boolean, default=True)
    
    last_checked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
