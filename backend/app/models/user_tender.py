from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class UserTender(Base):
    """
    Модель для персонального CRM — связь пользователя с тендером.
    Позволяет сохранять тендеры в избранное, менять статусы воронки и писать заметки.
    """
    __tablename__ = "user_tenders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), index=True)
    
    # Статус в воронке: saved, preparing, submitted, won, lost
    status = Column(String(50), default="saved")
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
