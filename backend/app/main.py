"""
Тендерный Хакер - Главный модуль FastAPI приложения
"""
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from datetime import datetime
import os
import logging
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import router as api_router
from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import setup_logging
from app.core.limiter import limiter

from contextlib import asynccontextmanager
import asyncio
from app.worker import worker_loop

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование
setup_logging()
logger = logging.getLogger(__name__)

# Настройка Sentry (только для production)
if not settings.DEBUG and settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1,  # 10% транзакций для производительности
            profiles_sample_rate=0.1,
        )
        logger.info("Sentry monitoring initialized")
    except ImportError:
        logger.warning("Sentry SDK not installed, skipping Sentry initialization")
    except Exception as e:
        logger.warning(f"Failed to initialize Sentry: {e}")

# Настройка CSRF защиты (опционально)
try:
    from fastapi_csrf_protect import CsrfProtect, CsrfProtectError
    
    @CsrfProtect.load_config
    def get_csrf_config():
        return {
            "secret_key": settings.CSRF_SECRET_KEY,
            "cookie_secure": not settings.DEBUG,  # HTTPS только в production
            "cookie_samesite": "lax"
        }
    
    csrf_protect = CsrfProtect()
    logger.info("CSRF protection enabled")
except ImportError:
    logger.warning("fastapi-csrf-protect not installed, CSRF protection disabled")
    csrf_protect = None
    CsrfProtectError = None
except Exception as e:
    logger.warning(f"Failed to initialize CSRF protection: {e}")
    csrf_protect = None
    CsrfProtectError = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем фоновый воркер для проверки подписок
    # Интервал: 1 час (3600 секунд)
    worker_task = asyncio.create_task(worker_loop(interval_seconds=3600))
    logger.info("Background worker started via lifespan.")
    yield
    # При выключении можно отменить таск
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Background worker stopped.")

app = FastAPI(
    title="Тендерный Хакер API",
    description="AI-ассистент для анализа госзакупок",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Добавляем middleware для rate limiting
from slowapi.middleware import SlowAPIMiddleware
app.add_middleware(SlowAPIMiddleware)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # Добавлен PATCH для обновления пользователя
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],  # Добавлен Accept
    expose_headers=["*"],  # Разрешаем все заголовки в ответе
)

# Глобальные обработчики ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTP исключений"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "status_code": 422,
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик всех остальных исключений"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error" if not settings.DEBUG else str(exc),
            "status_code": 500,
            "path": str(request.url.path)
        }
    )

# Добавляем обработчик ошибок CSRF
try:
    from fastapi_csrf_protect import CsrfProtectError
    
    @app.exception_handler(CsrfProtectError)
    async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message}
        )
except ImportError:
    pass  # CSRF protection не установлен

# Подключаем роутеры
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Тендерный Хакер API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check(request: Request, db: Session = Depends(get_db)):
    """Проверка здоровья сервиса с реальными проверками"""
    from app.core.redis_client import redis_client
    from sqlalchemy import text

    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

    # Проверка базы данных
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Проверка Redis
    try:
        redis_client.client.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded" if health_status["database"] == "connected" else "unhealthy"

    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
