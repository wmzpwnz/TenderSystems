"""
Настройка логирования
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging():
    """Настройка логирования для приложения"""
    # Создаем директорию для логов если её нет
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Формат логов
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Определяем уровень логирования из переменной окружения
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Ротация файлов: 10MB, максимум 5 файлов
    file_handler = RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Консольный handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Настройка root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.handlers = []  # Очищаем существующие handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Уменьшаем уровень логирования для некоторых библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)











