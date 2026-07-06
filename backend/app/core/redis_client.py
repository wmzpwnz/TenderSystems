"""
Клиент Redis для кэширования
"""
import redis
from app.core.config import settings
import json
from typing import Optional, Any


class RedisClient:
    """Клиент для работы с Redis"""
    
    def __init__(self):
        self.client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5
        )
    
    def get(self, key: str) -> Optional[str]:
        """Получить значение по ключу"""
        try:
            return self.client.get(key)
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ex: int = 3600) -> bool:
        """Установить значение с TTL"""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            return self.client.set(key, value, ex=ex)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """Удалить ключ"""
        try:
            return bool(self.client.delete(key))
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """Проверить существование ключа"""
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False


# Глобальный экземпляр клиента
redis_client = RedisClient()















