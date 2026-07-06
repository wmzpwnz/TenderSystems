"""
Celery задачи для синхронизации данных с ЕИС
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.tender import Tender
from app.services.eis_client import EISClient

logger = logging.getLogger(__name__)


@celery_app.task(name="sync_new_tenders", bind=True)
def sync_new_tenders_task(self, region: Optional[str] = None, limit: int = 50):
    """
    Синхронизация новых тендеров с ЕИС

    Args:
        region: Код региона (77 - Москва, 78 - СПб и т.д.)
        limit: Максимальное количество тендеров для синхронизации

    Returns:
        Dict с результатами синхронизации
    """
    try:
        logger.info(f"Starting sync_new_tenders task, region={region}, limit={limit}")

        # Создаем event loop для async функций
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            _sync_new_tenders_async(region=region, limit=limit)
        )

        loop.close()

        logger.info(f"Sync completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in sync_new_tenders_task: {e}", exc_info=True)
        self.retry(countdown=300, max_retries=3)  # Retry after 5 minutes


async def _sync_new_tenders_async(region: Optional[str] = None, limit: int = 50):
    """Асинхронная функция синхронизации новых тендеров"""
    db = SessionLocal()
    eis_client = EISClient()

    try:
        # Загружаем новые тендеры
        from app.schemas.tender import TenderFilter
        from datetime import date as date_type
        today = date_type.today()

        if region:
            regions = [region]
        else:
            # Популярные регионы для синхронизации
            regions = ["77", "78", "50", "72", "23", "66"]  # Москва, СПб, МО, Тюмень, Краснодар, Екат

        new_count = 0
        updated_count = 0
        error_count = 0

        for reg in regions:
            try:
                logger.info(f"Syncing tenders for region {reg}")

                # Создаём TenderFilter для поиска
                filters = TenderFilter(
                    region=reg,
                    page=1,
                    page_size=limit,
                    date_from=today,
                    date_to=today
                )
                
                result = await eis_client.search_tenders(filters)
                tenders_data = result.get("items", []) if isinstance(result, dict) else result

                for tender_data in tenders_data:
                    try:
                        eis_id = tender_data.get('eis_id') or tender_data.get('id') or tender_data.get('number')

                        if not eis_id:
                            logger.warning(f"Tender without eis_id: {tender_data}")
                            continue

                        # Проверяем, существует ли тендер
                        existing = db.query(Tender).filter(Tender.eis_id == eis_id).first()

                        if existing:
                            # Обновляем существующий
                            for key, value in tender_data.items():
                                if hasattr(existing, key) and value is not None:
                                    setattr(existing, key, value)
                            existing.updated_at = datetime.utcnow()
                            updated_count += 1
                            logger.debug(f"Updated tender {eis_id}")
                        else:
                            # Создаем новый
                            new_tender = Tender(**eis_client.parse_tender_data(tender_data))
                            db.add(new_tender)
                            new_count += 1
                            logger.info(f"Created new tender {eis_id}")

                        db.commit()

                    except Exception as e:
                        logger.error(f"Error processing tender: {e}")
                        db.rollback()
                        error_count += 1
                        continue

                # Задержка между регионами
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error syncing region {reg}: {e}")
                continue

        return {
            "new": new_count,
            "updated": updated_count,
            "errors": error_count,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in _sync_new_tenders_async: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="refresh_incomplete_tenders", bind=True)
def refresh_incomplete_tenders_task(self, limit: int = 50):
    """
    Обновление тендеров с неполными данными через HTML парсинг

    Args:
        limit: Максимальное количество тендеров для обновления

    Returns:
        Dict с результатами обновления
    """
    try:
        logger.info(f"Starting refresh_incomplete_tenders task, limit={limit}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            _refresh_incomplete_tenders_async(limit=limit)
        )

        loop.close()

        logger.info(f"Refresh completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in refresh_incomplete_tenders_task: {e}", exc_info=True)
        self.retry(countdown=600, max_retries=2)


async def _refresh_incomplete_tenders_async(limit: int = 50):
    """Асинхронная функция обновления неполных тендеров"""
    db = SessionLocal()
    eis_client = EISClient()

    try:
        # Находим тендеры с пустыми полями
        tenders_to_update = db.query(Tender).filter(
            (Tender.customer_name.is_(None)) |
            (Tender.customer_region.is_(None)) |
            (Tender.initial_price.is_(None)) |
            (Tender.platform.is_(None)) |
            (Tender.prepayment_type.is_(None))
        ).limit(limit).all()

        logger.info(f"Found {len(tenders_to_update)} incomplete tenders")

        updated_count = 0

        for tender in tenders_to_update:
            try:
                # Загружаем детальную информацию
                detail_data = await eis_client.get_tender_details(tender.eis_id)

                if detail_data:
                    detail_parsed = eis_client.parse_tender_data(detail_data)

                    # Обновляем пустые поля
                    updated = False
                    for key, value in detail_parsed.items():
                        if value is not None and hasattr(tender, key):
                            current_value = getattr(tender, key, None)
                            if current_value is None:
                                setattr(tender, key, value)
                                updated = True

                    if updated:
                        tender.updated_at = datetime.utcnow()
                        db.commit()
                        updated_count += 1
                        logger.info(f"Updated tender {tender.eis_id}")

                # Задержка между запросами
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error updating tender {tender.eis_id}: {e}")
                db.rollback()
                continue

        return {
            "updated": updated_count,
            "total": len(tenders_to_update),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in _refresh_incomplete_tenders_async: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="cleanup_old_tenders")
def cleanup_old_tenders_task(days: int = 180):
    """
    Удаление старых завершенных тендеров

    Args:
        days: Удалить тендеры старше N дней

    Returns:
        Dict с количеством удаленных записей
    """
    try:
        logger.info(f"Starting cleanup_old_tenders task, days={days}")

        db = SessionLocal()

        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            deleted = db.query(Tender).filter(
                Tender.status.in_(['completed', 'cancelled']),
                Tender.publication_date < cutoff_date
            ).delete(synchronize_session=False)

            db.commit()

            logger.info(f"Deleted {deleted} old tenders")

            return {
                "deleted": deleted,
                "cutoff_date": cutoff_date.isoformat(),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in cleanup_old_tenders_task: {e}", exc_info=True)
        return {"error": str(e)}
