#!/usr/bin/env python3
"""Тестовый скрипт для проверки работы EIS API"""
import asyncio
import logging
import os
import sys

# Добавляем путь к приложению
sys.path.insert(0, '/app')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_soap_api():
    """Тестирует SOAP API"""
    from app.services.eis_soap_client import EISSOAPClient
    
    token = os.getenv("EIS_SOAP_TOKEN", "")
    logger.info("SOAP token is configured" if token else "No SOAP token!")
    
    if not token:
        logger.error("EIS_SOAP_TOKEN not set!")
        return
    
    client = EISSOAPClient(token=token)
    
    # Тестируем получение документов по региону
    logger.info("Testing getDocsByOrgRegion for region 77 (Moscow)...")
    archive_url = await client.get_docs_by_org_region(
        org_region="77",
        document_type="epNotificationEF2020"
    )
    
    if archive_url:
        logger.info(f"Got archive URL: {archive_url[:100]}...")
        # Скачиваем и парсим архив
        tenders = client.download_and_parse_archive(archive_url)
        logger.info(f"Parsed {len(tenders)} tenders from archive")
        if tenders:
            for tender in tenders[:3]:
                logger.info(f"  - {tender.get('id')}: {tender.get('title', '')[:50]}")
    else:
        logger.error("No archive URL returned!")

async def test_html_parsing():
    """Тестирует HTML парсинг"""
    from app.services.eis_client import EISClient
    from app.schemas.tender import TenderFilter
    
    logger.info("Testing HTML parsing...")
    
    client = EISClient()
    client.use_html_parsing = True
    client.use_soap = False
    client.soap_client = None
    
    filters = TenderFilter(page=1, page_size=10)
    result = await client._search_via_html(filters)
    
    logger.info(f"HTML parsing result: {len(result.get('items', []))} items, total: {result.get('total')}")
    for item in result.get('items', [])[:3]:
        logger.info(f"  - {item.get('id')}: {item.get('title', '')[:50]}")

async def main():
    logger.info("=" * 50)
    logger.info("Testing EIS API Integration")
    logger.info("=" * 50)
    
    try:
        await test_soap_api()
    except Exception as e:
        logger.error(f"SOAP API test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("=" * 50)
    
    try:
        await test_html_parsing()
    except Exception as e:
        logger.error(f"HTML parsing test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
