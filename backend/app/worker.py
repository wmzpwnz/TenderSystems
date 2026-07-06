import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.search_subscription import SearchSubscription
from app.models.user import User
from app.services.eis_client import EISClient
from app.schemas.tender import TenderFilter
from app.services.notification_service import notification_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.worker")

async def process_subscriptions():
    """
    Основная логика обработки подписок
    """
    db = SessionLocal()
    try:
        # 1. Получаем активные подписки
        subscriptions = db.query(SearchSubscription).filter(SearchSubscription.is_active == True).all()
        
        if not subscriptions:
            # logger.info("No active subscriptions found.")
            return
            
        eis_client = EISClient()
        
        for sub in subscriptions:
            try:
                logger.info(f"Checking subscription '{sub.name}' for user {sub.user_id}")
                
                # 2. Подготовка фильтров
                filters_dict = sub.filters.copy()
                
                # Убеждаемся, что ищем только свежие
                # Если уже проверяли - ищем с даты последней проверки
                # Иначе - за последние 24 часа
                if sub.last_checked_at:
                    filters_dict['date_from'] = sub.last_checked_at.date()
                else:
                    # По умолчанию за сегодня
                    filters_dict['date_from'] = datetime.now(timezone.utc).date()
                
                # Ограничиваем количество для проверки
                filters_dict['page_size'] = 50
                
                tender_filter = TenderFilter(**filters_dict)
                
                # 3. Поиск в ЕИС
                results = await eis_client.search_tenders(tender_filter)
                items = results.get("items", [])
                
                if items:
                    # Фильтруем те, что действительно "новые" (по времени публикации, если есть)
                    # Или просто по факту наличия в результатах
                    new_items = []
                    if sub.last_checked_at:
                        last_checked = sub.last_checked_at
                        if last_checked.tzinfo is None:
                            last_checked = last_checked.replace(tzinfo=timezone.utc)
                    else:
                        last_checked = None

                    for item in items:
                        # Если есть время публикации, проверяем точно
                        pub_date = item.get('publication_date')
                        if pub_date and last_checked:
                            # Парсим дату если это строка
                            if isinstance(pub_date, str):
                                try:
                                    pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                                except:
                                    # Если не вышло, считаем новым
                                    new_items.append(item)
                                    continue
                            
                            # Приводим к aware если она naive
                            if pub_date.tzinfo is None:
                                pub_date = pub_date.replace(tzinfo=timezone.utc)

                            if pub_date > last_checked:
                                new_items.append(item)
                        else:
                            # Если нет даты для сравнения, считаем весь первый батч новым (если не было проверок)
                            if not last_checked:
                                new_items.append(item)
                    
                    if new_items:
                        logger.info(f"Found {len(new_items)} new tenders for user {sub.user_id}")
                        
                        # Получаем данные пользователя для уведомления
                        user = db.query(User).filter(User.id == sub.user_id).first()
                        if user:
                            # 4. Отправка уведомления
                            await notification_service.notify_new_tenders(
                                user_id=user.id,
                                subscription_name=sub.name,
                                tenders=new_items,
                                chat_id=user.telegram_chat_id
                            )
                
                # 5. Обновляем время последней проверки
                sub.last_checked_at = datetime.now(timezone.utc)
                db.commit()
                
            except Exception as e:
                logger.error(f"Error processing subscription {sub.id}: {e}", exc_info=True)
                db.rollback()
                
    finally:
        db.close()

async def worker_loop(interval_seconds: int = 3600):
    """
    Бесконечный цикл воркера
    """
    logger.info(f"Starting background worker. Check interval: {interval_seconds}s")
    while True:
        try:
            await process_subscriptions()
            await asyncio.sleep(interval_seconds)
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            # Задержка перед повтором при ошибке (60 секунд)
            await asyncio.sleep(60)

if __name__ == "__main__":
    # Для запуска как отдельного процесса: python -m app.worker
    asyncio.run(worker_loop())
