"""
Тестовый скрипт для проверки подключения к API ЕИС
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).parent))

from app.services.eis_client import EISClient
from app.core.logging_config import setup_logging

setup_logging()


async def test_eis_connection():
    """Тестирование подключения к API ЕИС"""
    print("=" * 60)
    print("Тестирование подключения к API ЕИС")
    print("=" * 60)
    
    client = EISClient()
    
    # Тест 1: Поиск тендеров
    print("\n1. Тест поиска тендеров...")
    try:
        result = await client.search_tenders(page=1, page_size=5)
        
        if result and result.get("items"):
            print(f"✅ Успешно! Найдено тендеров: {len(result['items'])}")
            print(f"   Всего в системе: {result.get('total', 'неизвестно')}")
            
            # Показываем первый тендер
            if result["items"]:
                first_tender = result["items"][0]
                print(f"\n   Пример тендера:")
                print(f"   - ID: {first_tender.get('id', 'N/A')}")
                print(f"   - Название: {first_tender.get('purchaseObjectInfo', first_tender.get('title', 'N/A'))[:50]}")
        else:
            print("⚠️  Получен пустой ответ или неверный формат")
            print(f"   Ответ: {result}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    # Тест 2: Получение деталей тендера (если есть ID)
    print("\n2. Тест получения деталей тендера...")
    try:
        result = await client.search_tenders(page=1, page_size=1)
        if result and result.get("items"):
            tender_id = result["items"][0].get("id")
            if tender_id:
                print(f"   Получаем детали тендера ID: {tender_id}")
                details = await client.get_tender_details(str(tender_id))
                
                if details:
                    print("✅ Детали получены успешно")
                    print(f"   Ключи в ответе: {list(details.keys())[:10]}")
                else:
                    print("⚠️  Пустой ответ")
            else:
                print("⚠️  Не найден ID тендера для теста")
        else:
            print("⚠️  Нет тендеров для теста")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Тест 3: Получение документов
    print("\n3. Тест получения документов...")
    try:
        result = await client.search_tenders(page=1, page_size=1)
        if result and result.get("items"):
            tender_id = result["items"][0].get("id")
            if tender_id:
                print(f"   Получаем документы тендера ID: {tender_id}")
                documents = await client.get_tender_documents(str(tender_id))
                
                if documents:
                    print(f"✅ Найдено документов: {len(documents)}")
                    for i, doc in enumerate(documents[:3], 1):
                        doc_name = doc.get("fileName") or doc.get("name") or "Неизвестно"
                        print(f"   {i}. {doc_name}")
                else:
                    print("⚠️  Документы не найдены")
            else:
                print("⚠️  Не найден ID тендера для теста")
        else:
            print("⚠️  Нет тендеров для теста")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n" + "=" * 60)
    print("Тестирование завершено")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_eis_connection())







