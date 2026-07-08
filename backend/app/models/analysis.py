"""
Модель для хранения результатов AI-анализа
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Analysis(Base):
    """Результаты анализа тендера"""
    
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Основные результаты анализа
    summary = Column(Text)  # Краткое описание (1 предложение)
    critical_requirements = Column(JSON)  # Критические требования
    deadlines = Column(JSON)  # Анализ сроков
    financial_info = Column(JSON)  # Финансовая информация
    evaluation_criteria = Column(JSON)  # Критерии оценки
    risks = Column(JSON)  # Подводные камни
    
    # Дополнительная аналитика
    margin_analysis = Column(JSON)  # Анализ маржинальности
    win_probability = Column(Numeric(5, 2))  # Вероятность победы (0-100)
    risk_level = Column(String(20))  # low, medium, high
    
    # Метаданные анализа
    raw_ai_response = Column(JSON)  # Полный ответ от AI
    analysis_version = Column(String(20), default="1.0")
    analysis_type = Column(String(20), default="quick")  # 'quick' или 'deep'
    documents_analyzed = Column(JSON)  # Список обработанных документов
    documents_hash = Column(String(64), nullable=True)  # Хэш исходного набора документов
    source_documents_count = Column(Integer, nullable=True)  # Количество документов в исходном наборе
    cost_breakdown = Column(JSON)  # Разбивка по позициям для глубокого анализа
    created_at = Column(DateTime, server_default=func.now())
    
    # Связь с тендером
    tender = relationship("Tender", backref="analyses")
    
    def __repr__(self):
        return f"<Analysis for Tender {self.tender_id}>"
