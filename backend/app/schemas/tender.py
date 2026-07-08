"""
Pydantic схемы для тендеров
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Union
from datetime import datetime, date
from decimal import Decimal


class TenderBase(BaseModel):
    """Базовая схема тендера"""
    eis_id: str
    number: Optional[str] = None
    title: str
    description: Optional[str] = None


class TenderCreate(TenderBase):
    """Схема для создания тендера"""
    customer_name: Optional[str] = None
    customer_inn: Optional[str] = None
    customer_region: Optional[str] = None
    initial_price: Optional[Decimal] = None
    currency: str = "RUB"
    guarantee_amount: Optional[Decimal] = None
    contract_guarantee: Optional[Decimal] = None
    publication_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    contract_deadline: Optional[datetime] = None
    status: str = "active"
    procedure_type: Optional[str] = None
    documents_url: Optional[str] = None
    documents_data: Optional[List[Dict]] = None
    okpd2_codes: Optional[List[str]] = None
    requirements: Optional[Dict] = None
    platform: Optional[str] = None
    prepayment_type: Optional[str] = None
    preferences: Optional[List[str]] = None


class TenderResponse(TenderBase):
    """Схема ответа с данными тендера"""
    id: int
    customer_name: Optional[str] = None
    customer_inn: Optional[str] = None
    customer_region: Optional[str] = None
    initial_price: Optional[Decimal] = None
    currency: str = "RUB"
    guarantee_amount: Optional[Decimal] = None
    contract_guarantee: Optional[Decimal] = None
    publication_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    contract_deadline: Optional[datetime] = None
    status: str
    procedure_type: Optional[str] = None
    documents_url: Optional[str] = None
    documents_data: Optional[List[Dict]] = None
    okpd2_codes: Optional[List[str]] = None
    requirements: Optional[Dict] = None
    platform: Optional[str] = None  # Площадка (Росэлторг, Сбербанк-АСТ и т.д.)
    prepayment_type: Optional[str] = None  # Тип авансирования
    preferences: Optional[List[str]] = None  # Преимущества (СМП, СОНКО и т.д.)
    is_analyzed: bool = False
    is_favorite: bool = False
    crm_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    url: Optional[str] = None  # URL на zakupki.gov.ru для Live Search
    analysis_risk_level: Optional[str] = None
    analysis_summary: Optional[str] = None
    analysis_margin_analysis: Optional[Union[Dict, str, Any]] = None
    
    class Config:
        from_attributes = True


class TenderListResponse(BaseModel):
    """Схема ответа со списком тендеров"""
    items: List[TenderResponse]
    total: int
    page: int
    page_size: int
    pages: Optional[int] = None
    search_time_ms: Optional[float] = None


class TenderFilter(BaseModel):
    """Схема фильтров для поиска тендеров"""
    page: int = 1
    page_size: int = 20
    
    # Текстовый поиск
    query: Optional[str] = None  # Основной запрос
    keywords: Optional[List[str]] = None  # Список ключевых слов (AND)
    exclude_words: Optional[List[str]] = None  # Исключить слова
    
    # Финансы
    price_from: Optional[Decimal] = None
    price_to: Optional[Decimal] = None
    currency: Optional[str] = None
    
    # Даты
    date_from: Optional[date] = None  # Дата публикации от
    date_to: Optional[date] = None    # Дата публикации до
    
    # Заказчик и Регион
    customer_inn: Optional[str] = None
    region: Optional[str] = None      # Код региона или название
    regions: Optional[List[str]] = None # Список регионов
    
    # Классификация
    okpd2: Optional[str] = None
    okpd2_codes: Optional[List[str]] = None
    
    # Законодательство
    fz44: bool = True
    fz223: bool = True
    
    # Статус торга
    status: Optional[str] = None # active, completed
    
    # Дополнительные фильтры
    customer_name: Optional[str] = None  # Название заказчика
    platform: Optional[str] = None  # Площадка
    deadline_less_than_days: Optional[int] = None  # Дедлайн меньше N дней
    guarantee_from: Optional[Decimal] = None  # Обеспечение заявки от
    guarantee_to: Optional[Decimal] = None  # Обеспечение заявки до
    contract_guarantee_from: Optional[Decimal] = None  # Обеспечение контракта от
    contract_guarantee_to: Optional[Decimal] = None  # Обеспечение контракта до
    prepayment_type: Optional[str] = None  # Тип авансирования
    preferences: Optional[List[str]] = None  # Преимущества (СМП/СОНКО и т.д.)
    procedure_types: Optional[List[str]] = None  # Способ отбора

