"""
Тестовый скрипт для изучения структуры XML в архивах
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.eis_soap_client import EISSOAPClient
from app.core.logging_config import setup_logging
import xml.etree.ElementTree as ET
import zipfile
import io

setup_logging()


async def test_parse_archive():
    """Тестирование парсинга архива"""
    print("=" * 60)
    print("Изучение структуры XML в архивах")
    print("=" * 60)
    
    token = os.getenv("EIS_SOAP_TOKEN", "")
    if not token:
        print("❌ EIS_SOAP_TOKEN не установлен")
        return

    client = EISSOAPClient(token=token)
    
    # Получаем архив
    print("\n1. Получение ссылки на архив...")
    archive_url = await client.get_docs_by_org_region(
        org_region="77",
        date="2024-12-08"
    )
    
    if not archive_url:
        print("❌ Не удалось получить архив")
        return
    
    print(f"✅ Получена ссылка: {archive_url[:80]}...")
    
    # Скачиваем архив
    print("\n2. Скачивание архива...")
    archive_data = await client._download_archive(archive_url)
    
    if not archive_data:
        print("❌ Не удалось скачать архив")
        return
    
    print(f"✅ Архив скачан, размер: {len(archive_data)} байт")
    
    # Распаковываем и изучаем структуру
    print("\n3. Изучение структуры XML файлов...")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_data), 'r') as zip_ref:
            xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
            print(f"Найдено XML файлов: {len(xml_files)}")
            
            if xml_files:
                # Берем первый файл для изучения
                first_file = xml_files[0]
                print(f"\nИзучаем файл: {first_file}")
                
                xml_content = zip_ref.read(first_file)
                root = ET.fromstring(xml_content)
                
                # Выводим структуру
                print("\nСтруктура XML:")
                print("=" * 60)
                print(f"Корневой элемент: {root.tag}")
                print(f"Атрибуты: {root.attrib}")
                
                # Ищем все элементы и их текстовое содержимое
                print("\nЭлементы верхнего уровня:")
                for child in root:
                    print(f"  - {child.tag}: {child.text[:100] if child.text else 'None'}")
                
                # Ищем namespace
                print("\nNamespace:")
                for prefix, uri in root.attrib.items():
                    if 'xmlns' in prefix:
                        print(f"  {prefix}: {uri}")
                
                # Ищем конкретные поля
                print("\nПоиск ключевых полей:")
                fields_to_find = [
                    'registrationNumber',
                    'purchaseObjectInfo',
                    'name',
                    'fullName',
                    'customerName',
                    'initialPrice',
                    'price',
                    'publishDate',
                    'publicationDate',
                    'applicationDeadline',
                    'deadline'
                ]
                
                for field in fields_to_find:
                    # Ищем без namespace
                    found = root.find(f'.//{field}')
                    if found is not None:
                        print(f"  ✅ {field}: {found.text[:80] if found.text else 'None'}")
                    else:
                        # Ищем с namespace
                        for prefix, uri in root.attrib.items():
                            if 'xmlns' in prefix:
                                ns = {prefix.replace('xmlns:', ''): uri}
                                found = root.find(f'.//{{{uri}}}{field}', ns)
                                if found is not None:
                                    print(f"  ✅ {field} (ns:{prefix}): {found.text[:80] if found.text else 'None'}")
                                    break
                
                # Сохраняем пример XML для изучения
                with open('example_notification.xml', 'wb') as f:
                    f.write(xml_content)
                print(f"\n✅ Пример XML сохранен в example_notification.xml")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_parse_archive())






