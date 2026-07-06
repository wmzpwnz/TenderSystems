"""
Тестовый скрипт для проверки SOAP API ЕИС
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).parent))

from app.services.eis_soap_client import EISSOAPClient
from app.core.logging_config import setup_logging

setup_logging()


async def test_soap_api():
    """Тестирование SOAP API ЕИС"""
    print("=" * 60)
    print("Тестирование SOAP API ЕИС")
    print("=" * 60)
    
    token = os.getenv("EIS_SOAP_TOKEN", "")
    
    if not token:
        print("❌ Токен не найден! Установите EIS_SOAP_TOKEN в .env")
        return
    
    print("\nТокен: найден в окружении")
    print(f"Тип пользователя: IP (Физическое лицо/ИП)")
    
    # Создаем клиент для физического лица (IP)
    client = EISSOAPClient(token=token, user_type='IP')
    
    # Тест 1: Получение документов по региону
    print("\n1. Тест получения документов по региону (Москва)...")
    try:
        archive_url = await client.get_docs_by_org_region(
            org_region="77",  # Москва
            date="2025-12-08"  # Сегодня
        )
        
        if archive_url:
            print(f"✅ Успешно! Получена ссылка на архив:")
            print(f"   {archive_url[:80]}...")
            
            # Тест 2: Скачивание и парсинг архива
            print("\n2. Тест скачивания и парсинга архива...")
            try:
                tenders = client.download_and_parse_archive(archive_url)
                
                if tenders:
                    print(f"✅ Успешно! Найдено тендеров: {len(tenders)}")
                    print(f"\n   Примеры тендеров:")
                    for i, tender in enumerate(tenders[:3], 1):
                        print(f"\n   Тендер {i}:")
                        print(f"   - ID: {tender.get('id', 'N/A')}")
                        print(f"   - Название: {tender.get('title', tender.get('purchaseObjectInfo', 'N/A'))[:60]}")
                        print(f"   - Заказчик: {tender.get('customerName', 'N/A')[:40]}")
                        if tender.get('price'):
                            print(f"   - Цена: {tender['price']:,.0f} руб.")
                        if tender.get('publishDate'):
                            print(f"   - Дата публикации: {tender['publishDate']}")
                else:
                    print("⚠️  Архив скачан, но тендеры не найдены")
                    print("   Возможно, архив пуст или структура XML отличается")
            except Exception as e:
                print(f"❌ Ошибка при скачивании/парсинге архива: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️  Не удалось получить ссылку на архив")
            print("   Проверьте токен и параметры запроса")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 3: Поиск тендеров через search_tenders
    print("\n3. Тест поиска тендеров (search_tenders)...")
    try:
        tenders = await client.search_tenders(
            region="77",  # Москва
            date="2025-12-08",  # Сегодня
            limit=5
        )
        
        if tenders:
            print(f"✅ Успешно! Найдено тендеров: {len(tenders)}")
            for i, tender in enumerate(tenders[:2], 1):
                print(f"\n   Тендер {i}:")
                print(f"   - ID: {tender.get('id', 'N/A')}")
                print(f"   - Название: {tender.get('title', 'N/A')[:50]}")
        else:
            print("⚠️  Тендеры не найдены")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Тестирование завершено")
    print("=" * 60)
    print("\n💡 Совет: Если тесты прошли успешно, система готова к работе!")
    print("   Запустите: docker-compose up -d")


if __name__ == "__main__":
    asyncio.run(test_soap_api())
