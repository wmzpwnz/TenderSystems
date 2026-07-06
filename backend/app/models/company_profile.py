"""
Модель профиля компании для персонализации анализа
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class CompanyProfile(Base):
    """Профиль компании для сравнения с требованиями тендеров"""
    
    __tablename__ = "company_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Основная информация
    name = Column(String(500))  # Название компании
    inn = Column(String(20), index=True)  # ИНН
    region = Column(String(100))  # Регион работы
    
    # Лицензии и допуски
    licenses = Column(JSON)  # Список лицензий (например: ["ФСБ", "МЧС"])
    sro_certificates = Column(JSON)  # Допуски СРО (например: ["СРО-С-12345"])
    
    # Опыт работы
    experience_contracts = Column(Integer, default=0)  # Количество выполненных контрактов
    experience_sum = Column(Numeric(15, 2))  # Сумма выполненных контрактов
    
    # Специализация
    okpd2_codes = Column(JSON)  # Коды ОКПД2 специализации
    
    # Ресурсы
    equipment = Column(JSON)  # Оборудование в наличии
    
    # Метаданные
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<CompanyProfile {self.name or 'Unnamed'}>"









