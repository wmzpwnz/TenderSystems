"""
Скрипт для обновления всех тендеров с пустыми полями через HTML парсинг детальных страниц
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.tender import Tender
from app.services.eis_client import EISClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def refresh_all_tenders(limit: int = 100):
    """Обновляет все тендеры с пустыми полями"""
    db = SessionLocal()
    eis_client = EISClient()
    
    try:
        # Находим тендеры с пустыми полями
        tenders_to_update = db.query(Tender).filter(
            (Tender.customer_name.is_(None)) |
            (Tender.customer_region.is_(None)) |
            (Tender.initial_price.is_(None)) |
            (Tender.publication_date.is_(None)) |
            (Tender.application_deadline.is_(None))
        ).limit(limit).all()
        
        logger.info(f"Найдено {len(tenders_to_update)} тендеров для обновления")
        
        updated_count = 0
        
        for i, tender in enumerate(tenders_to_update, 1):
            try:
                logger.info(f"[{i}/{len(tenders_to_update)}] Загрузка деталей для тендера {tender.eis_id}")
                
                # Загружаем детальную информацию через HTML парсинг
                detail_data = await eis_client.get_tender_details(tender.eis_id)
                
                if detail_data:
                    detail_parsed = eis_client.parse_tender_data(detail_data)
                    
                    # Обновляем пустые поля
                    updated = False
                    updated_fields = []
                    for key, value in detail_parsed.items():
                        if value is not None:
                            current_value = getattr(tender, key, None)
                            # Обновляем если значение было NULL или изменилось
                            if current_value is None or (key in ['customer_name', 'customer_region', 'initial_price', 'publication_date', 'application_deadline'] and current_value != value):
                                setattr(tender, key, value)
                                updated = True
                                updated_fields.append(key)
                    
                    if updated:
                        tender.updated_at = datetime.utcnow()
                        updated_count += 1
                        logger.info(f"✓ Обновлен тендер {tender.eis_id}, поля: {updated_fields}")
                    else:
                        logger.debug(f"  Нет обновлений для тендера {tender.eis_id}")
                else:
                    logger.warning(f"  Не удалось загрузить данные для тендера {tender.eis_id}")
                
                # Небольшая задержка, чтобы не перегружать сервер
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  Ошибка при обновлении тендера {tender.eis_id}: {e}")
                continue
        
        db.commit()
        
        logger.info(f"\n✓ Готово! Обновлено {updated_count} из {len(tenders_to_update)} тендеров")
        
        return updated_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Обновить тендеры с пустыми полями")
    parser.add_argument("--limit", type=int, default=100, help="Максимальное количество тендеров для обновления")
    
    args = parser.parse_args()
    
    asyncio.run(refresh_all_tenders(limit=args.limit))













