"""
Унифицированный парсер тендеров с fallback

Текущая стратегия:
1. SOAP API (метаданные + обновления) - основной способ
2. HTML парсинг (быстрый preview) - fallback

Философия: Не падаем, даже если один канал мёртв
"""
import asyncio
import logging
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from enum import Enum

from app.services.eis_soap_client import EISSOAPClient
from app.services.eis_html_parser import eis_html_parser
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class DataSource(str, Enum):
    """Источники данных"""
    SOAP = "soap"
    HTML = "html"
    CACHE = "cache"


class ParsingStrategy(str, Enum):
    """Стратегии парсинга"""
    BULK = "bulk"  # Массовая загрузка (SOAP по регионам)
    INCREMENTAL = "incremental"  # Инкрементальное обновление (SOAP)
    INSTANT = "instant"  # Мгновенный preview (HTML)


class UnifiedParser:
    """
    Умный парсер с автоматическим fallback

    Логика работы:
    - BULK режим (раз в день): SOAP по регионам → если failed → пропускаем
    - INCREMENTAL (каждый час): SOAP → если failed → пропускаем
    - INSTANT (по запросу): SOAP → если failed → HTML → если failed → cache
    """

    def __init__(self):
        self.soap_client = EISSOAPClient()
        self.html_parser = eis_html_parser

        # Статистика работы
        self.stats = {
            "soap_success": 0,
            "soap_failed": 0,
            "html_success": 0,
            "html_failed": 0,
            "total_tenders": 0
        }

    async def fetch_bulk_data(
        self,
        date: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Массовая загрузка тендеров (используется в cron/celery)

        Стратегия:
        1. Проверяем кеш (если use_cache=True)
        2. Загружаем через SOAP по всем регионам
        3. Возвращаем результат + источник данных

        Returns:
            {
                "source": DataSource,
                "tenders": List[Dict],
                "total": int,
                "errors": List[str]
            }
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        errors = []
        tenders = []
        source = None

        # Проверяем кеш
        cache_key = f"bulk_data:{date}"
        if use_cache:
            cached = await self._get_from_cache(cache_key)
            if cached:
                logger.info(f"✓ Returning cached bulk data for {date} ({len(cached)} tenders)")
                return {
                    "source": DataSource.CACHE,
                    "tenders": cached,
                    "total": len(cached),
                    "errors": []
                }

        # Загрузка через SOAP
        try:
            logger.info(f"Fetching via SOAP for {date}")
            soap_tenders = await self._fetch_from_soap_bulk(date)

            if soap_tenders and len(soap_tenders) > 0:
                tenders = soap_tenders
                source = DataSource.SOAP
                self.stats["soap_success"] += 1
                logger.info(f"✓ SOAP success: {len(tenders)} tenders")
            else:
                raise Exception("SOAP returned empty data")

        except Exception as e:
            logger.error(f"SOAP failed: {e}")
            errors.append(f"SOAP error: {str(e)}")
            self.stats["soap_failed"] += 1

        # Сохраняем в кеш (если что-то получили)
        if tenders:
            await self._save_to_cache(cache_key, tenders, ttl=86400)  # 24 часа
            self.stats["total_tenders"] += len(tenders)

        return {
            "source": source or DataSource.SOAP,
            "tenders": tenders,
            "total": len(tenders),
            "errors": errors
        }

    async def fetch_tender_instant(
        self,
        eis_id: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Мгновенная загрузка конкретного тендера для preview

        Стратегия:
        1. Проверяем кеш
        2. HTML парсинг (быстро, ~1-2 сек)
        3. Fallback на SOAP (медленнее, ~3-5 сек)
        4. Если всё failed → возвращаем None

        Args:
            eis_id: Номер закупки (например, "0372200111325000151")
            use_cache: Использовать кеш

        Returns:
            Dict с данными тендера или None
        """
        # Проверяем кеш
        if use_cache:
            cache_key = f"tender:{eis_id}"
            cached = await self._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Returning cached tender {eis_id}")
                return cached

        tender = None

        # Попытка 1: HTML парсинг (самый быстрый)
        if self.html_parser:
            try:
                logger.debug(f"Attempting HTML parsing for {eis_id}")
                tender = await self.html_parser.parse_tender(eis_id)

                if tender:
                    tender["_source"] = DataSource.HTML
                    self.stats["html_success"] += 1
                    logger.debug(f"✓ HTML parsing success for {eis_id}")
            except Exception as e:
                logger.debug(f"HTML parsing failed for {eis_id}: {e}")
                self.stats["html_failed"] += 1

        # Fallback на SOAP
        if not tender:
            try:
                logger.debug(f"Fallback to SOAP for {eis_id}")
                archive_url = await self.soap_client.get_docs_by_reestr_number(eis_id)

                if archive_url:
                    tenders = await self.soap_client.download_and_parse_archive(archive_url)
                    if tenders and len(tenders) > 0:
                        tender = tenders[0]  # Берём первый (обычно один)
                        tender["_source"] = DataSource.SOAP
                        self.stats["soap_success"] += 1
                        logger.debug(f"✓ SOAP fallback success for {eis_id}")
            except Exception as e:
                logger.warning(f"SOAP fallback failed for {eis_id}: {e}")
                self.stats["soap_failed"] += 1

        # Сохраняем в кеш
        if tender:
            cache_key = f"tender:{eis_id}"
            await self._save_to_cache(cache_key, tender, ttl=3600)  # 1 час

        return tender

    async def update_tender_status(
        self,
        eis_id: str
    ) -> Optional[Dict]:
        """
        Обновление статуса тендера (для INCREMENTAL режима)

        Используем только SOAP (он самый актуальный для статусов)
        """
        try:
            logger.debug(f"Updating status for {eis_id} via SOAP")
            archive_url = await self.soap_client.get_docs_by_reestr_number(eis_id)

            if archive_url:
                tenders = await self.soap_client.download_and_parse_archive(archive_url)
                if tenders and len(tenders) > 0:
                    tender = tenders[0]

                    # Обновляем кеш
                    cache_key = f"tender:{eis_id}"
                    await self._save_to_cache(cache_key, tender, ttl=3600)

                    return {
                        "eis_id": eis_id,
                        "status": tender.get("status"),
                        "updated_at": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"Error updating status for {eis_id}: {e}")

        return None

    # === Private methods ===

    async def _fetch_from_soap_bulk(self, date: str) -> List[Dict]:
        """
        Массовая загрузка через SOAP (по всем регионам)

        Стратегия: Параллельно запрашиваем все популярные регионы
        """
        # Топ-20 регионов по количеству закупок
        regions = [
            "77",  # Москва
            "78",  # Санкт-Петербург
            "50",  # Московская область
            "23",  # Краснодарский край
            "66",  # Свердловская область
            "74",  # Челябинская область
            "72",  # Тюменская область
            "52",  # Нижегородская область
            "16",  # Республика Татарстан
            "02",  # Республика Башкортостан
            "59",  # Пермский край
            "61",  # Ростовская область
            "63",  # Самарская область
            "47",  # Ленинградская область
            "54",  # Новосибирская область
            "38",  # Иркутская область
            "26",  # Ставропольский край
            "42",  # Кемеровская область
            "25",  # Приморский край
            "36",  # Воронежская область
        ]

        all_tenders = []

        # Запускаем параллельно (но с ограничением - не более 5 одновременно)
        semaphore = asyncio.Semaphore(5)

        async def fetch_region(region: str):
            async with semaphore:
                try:
                    logger.debug(f"Fetching SOAP data for region {region}, date {date}")
                    archive_url = await self.soap_client.get_docs_by_org_region(
                        org_region=region,
                        date=date
                    )

                    if archive_url:
                        tenders = await self.soap_client.download_and_parse_archive(archive_url)
                        logger.info(f"✓ Region {region}: {len(tenders)} tenders")
                        return tenders
                except Exception as e:
                    logger.warning(f"Error fetching region {region}: {e}")
                    return []

        # Запускаем параллельно
        tasks = [fetch_region(region) for region in regions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Собираем результаты
        for result in results:
            if isinstance(result, list):
                all_tenders.extend(result)

        # Удаляем дубликаты по eis_id
        unique_tenders = {}
        for tender in all_tenders:
            eis_id = tender.get("eis_id") or tender.get("id")
            if eis_id and eis_id not in unique_tenders:
                unique_tenders[eis_id] = tender

        logger.info(f"SOAP bulk: {len(all_tenders)} total, {len(unique_tenders)} unique")

        return list(unique_tenders.values())

    async def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Получить из Redis кеша"""
        try:
            if redis_client:
                data = await redis_client.get(key)
                if data:
                    import json
                    return json.loads(data)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        return None

    async def _save_to_cache(self, key: str, data: Dict, ttl: int = 3600):
        """Сохранить в Redis кеш"""
        try:
            if redis_client:
                import json
                await redis_client.set(key, json.dumps(data), ex=ttl)
        except Exception as e:
            logger.debug(f"Cache save error: {e}")

    def get_stats(self) -> Dict:
        """Получить статистику работы парсера"""
        total_requests = sum([
            self.stats["soap_success"],
            self.stats["soap_failed"],
            self.stats["html_success"],
            self.stats["html_failed"]
        ])

        return {
            **self.stats,
            "total_requests": total_requests,
            "soap_success_rate": (
                self.stats["soap_success"] / max(self.stats["soap_success"] + self.stats["soap_failed"], 1)
            ) * 100,
            "html_success_rate": (
                self.stats["html_success"] / max(self.stats["html_success"] + self.stats["html_failed"], 1)
            ) * 100,
        }


# Singleton instance
unified_parser = UnifiedParser()
