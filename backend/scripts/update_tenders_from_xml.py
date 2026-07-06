#!/usr/bin/env python3
"""
Скрипт для обновления существующих тендеров из XML файла
"""
import sys
import os
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).parent.parent))

from xml.etree import ElementTree as ET
from app.core.database import SessionLocal
from app.models.tender import Tender
from app.services.eis_soap_client import EISSOAPClient
from app.services.eis_client import EISClient
from datetime import datetime

def update_tenders_from_xml(xml_file_path: str):
    """Обновляет тендеры из XML файла"""
    db = SessionLocal()
    try:
        # Читаем XML
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Парсим XML через _parse_export_xml (правильный способ)
        client = EISSOAPClient()
        parsed_tenders = client._parse_export_xml(xml_content.encode('utf-8'))
        
        if not parsed_tenders:
            print("Не удалось распарсить данные из XML")
            return
        
        parsed_data = parsed_tenders[0]  # Берем первый тендер
        
        # Нормализуем данные
        eis_client = EISClient()
        tender_data = eis_client.parse_tender_data(parsed_data)
        
        if not tender_data.get("eis_id"):
            print("Нет ID тендера в данных")
            return
        
        # Ищем существующий тендер
        existing = db.query(Tender).filter(
            Tender.eis_id == tender_data["eis_id"]
        ).first()
        
        if existing:
            # Обновляем все поля
            updated_fields = []
            for key, value in tender_data.items():
                current_value = getattr(existing, key, None)
                if value is not None:
                    setattr(existing, key, value)
                    if current_value != value:
                        updated_fields.append(key)
            
            existing.updated_at = datetime.utcnow()
            db.commit()
            
            print(f"Обновлен тендер {tender_data['eis_id']}")
            print(f"Обновленные поля: {', '.join(updated_fields)}")
            print(f"Название: {tender_data.get('title', 'N/A')}")
            print(f"Заказчик: {tender_data.get('customer_name', 'N/A')}")
            print(f"Регион: {tender_data.get('customer_region', 'N/A')}")
            print(f"Цена: {tender_data.get('initial_price', 'N/A')}")
        else:
            # Создаем новый
            new_tender = Tender(**tender_data)
            db.add(new_tender)
            db.commit()
            print(f"Создан новый тендер {tender_data['eis_id']}")
    
    except Exception as e:
        db.rollback()
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "example_notification.xml"
    xml_path = Path(__file__).parent.parent / xml_file
    update_tenders_from_xml(str(xml_path))













