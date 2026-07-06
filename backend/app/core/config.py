"""
Конфигурация приложения
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://tenderuser:CHANGE_THIS_PASSWORD@localhost:5432/tenderdb"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # DeepSeek API
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL: str = os.getenv(
        "DEEPSEEK_API_URL",
        "https://api.deepseek.com/v1/chat/completions"
    )
    
    # ЕИС API
    EIS_API_KEY: str = os.getenv("EIS_API_KEY", "")
    EIS_API_URL: str = os.getenv(
        "EIS_API_URL",
        "https://zakupki.gov.ru/epz/api/mobile/proxy"
    )
    EIS_CERT_PATH: str = os.getenv("EIS_CERT_PATH", "")
    EIS_KEY_PATH: str = os.getenv("EIS_KEY_PATH", "")
    # SOAP API (официальный способ с токеном через ЕСИА)
    # ⚠️ С 01.01.2025 используются новые сервисы:
    # - getDocsIP для ФЛ: https://int.zakupki.gov.ru/eis-integration/services/getDocsIP
    # - getDocsLE для ЮЛ: https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE
    # Токены получаются в личном кабинете: https://zakupki.gov.ru/epz/opendata/search/results.html
    EIS_USE_SOAP: bool = os.getenv("EIS_USE_SOAP", "true").lower() == "true"
    EIS_SOAP_TOKEN: str = os.getenv("EIS_SOAP_TOKEN", "")  # Токен для физических лиц (ФЛ)
    EIS_SOAP_TOKEN_LE: str = os.getenv("EIS_SOAP_TOKEN_LE", "")  # Токен для юридических лиц (ЮЛ)
    EIS_SOAP_USER_TYPE: str = os.getenv("EIS_SOAP_USER_TYPE", "IP")  # IP (ФЛ) или LE (ЮЛ)
    
    # Другие методы
    EIS_USE_MOBILE_API: bool = os.getenv("EIS_USE_MOBILE_API", "false").lower() == "true"
    EIS_USE_HTML_PARSING: bool = os.getenv("EIS_USE_HTML_PARSING", "false").lower() == "true"
    EIS_BASE_URL: str = os.getenv(
        "EIS_BASE_URL",
        "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
    )
    
    # Application
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Default origins
    _allowed_origins_list: str = "http://localhost:3000,http://localhost:3002,http://localhost:8001,http://127.0.0.1:3000,http://127.0.0.1:3002,http://127.0.0.1:8001"
    
    ALLOWED_ORIGINS: Union[str, List[str]] = os.getenv(
        "ALLOWED_ORIGINS",
        _allowed_origins_list
    )
    
    API_V1_STR: str = "/api/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # File Upload
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Sentry
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "production")
    
    # CSRF
    CSRF_SECRET_KEY: str = os.getenv("CSRF_SECRET_KEY", SECRET_KEY)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

