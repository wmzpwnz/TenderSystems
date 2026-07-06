"""
Модель данных для тендеров
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Numeric, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Tender(Base):
    """Модель тендера из ЕИС"""
    
    __tablename__ = "tenders"
    
    id = Column(Integer, primary_key=True, index=True)
    eis_id = Column(String(100), unique=True, index=True, nullable=False)  # ID из ЕИС
    number = Column(String(100), index=True)  # Номер закупки
    title = Column(String(500), nullable=False)  # Наименование
    description = Column(Text)  # Описание
    
    # Заказчик
    customer_name = Column(String(500))
    customer_inn = Column(String(20), index=True)
    customer_region = Column(String(100))
    
    # Финансы
    initial_price = Column(Numeric(15, 2))  # Начальная цена
    currency = Column(String(10), default="RUB")
    guarantee_amount = Column(Numeric(15, 2))  # Обеспечение заявки
    contract_guarantee = Column(Numeric(15, 2))  # Обеспечение контракта
    
    # Сроки
    publication_date = Column(DateTime)
    application_deadline = Column(DateTime, index=True)
    contract_deadline = Column(DateTime)
    
    # Статус
    status = Column(String(50), index=True)  # active, completed, cancelled
    procedure_type = Column(String(100))  # Тип процедуры
    
    # Документы
    documents_url = Column(Text)  # Ссылка на документы
    documents_data = Column(JSON)  # Метаданные документов
    
    # Дополнительная информация
    okpd2_codes = Column(JSON)  # Коды ОКПД2
    requirements = Column(JSON)  # Требования (лицензии, СРО и т.д.)

    # Площадка и дополнительные параметры
    platform = Column(String(100))  # Площадка (РТС-тендер, Сбербанк-АСТ и т.д.)
    prepayment_type = Column(String(50))  # Тип авансирования (prepayment_44fz, prepayment_223fz, no_prepayment)
    preferences = Column(JSON)  # Преимущества и ограничения (СМП/СОНКО, УИС и т.д.)

    # Метаданные
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_analyzed = Column(Boolean, default=False)  # Проанализирован ли AI
    
    def __repr__(self):
        return f"<Tender {self.number}: {self.title[:50]}>"














