"""
Клиент для работы с API ЕИС zakupki.gov.ru

Поддерживает три режима работы:
1. Мобильное API (публичный доступ, без ЭЦП)
2. Партнерский API (требует ЭЦП и регистрацию)
3. HTML парсинг (запасной вариант)
"""
import httpx
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import ssl
import certifi
from pathlib import Path
import os
import re
from app.core.config import settings
import logging
from bs4 import BeautifulSoup
from app.services.eis_soap_client import EISSOAPClient
from app.schemas.tender import TenderFilter

logger = logging.getLogger(__name__)


class EISClient:
    """Клиент для работы с API ЕИС"""
    
    def __init__(self):
        # Определяем режим работы
        # С 01.01.2025 используются сервисы отдачи информации:
        # - getDocsIP для ФЛ: https://int.zakupki.gov.ru/eis-integration/services/getDocsIP
        # - getDocsLE для ЮЛ: https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE
        # Приоритет: SOAP API > HTML парсинг
        self.use_soap = os.getenv("EIS_USE_SOAP", "true").lower() == "true"
        self.soap_token = os.getenv("EIS_SOAP_TOKEN", "")
        self.soap_token_le = os.getenv("EIS_SOAP_TOKEN_LE", "")
        self.soap_user_type = os.getenv("EIS_SOAP_USER_TYPE", "IP")  # IP (ФЛ) или LE (ЮЛ)
        self.use_mobile_api = os.getenv("EIS_USE_MOBILE_API", "false").lower() == "true"
        # HTML парсинг используется как fallback, если SOAP недоступен
        self.use_html_parsing = os.getenv("EIS_USE_HTML_PARSING", "true").lower() == "true"
        
        # SOAP клиент (официальный способ с токеном через ЕСИА)
        # Выбираем токен в зависимости от типа пользователя
        token_to_use = self.soap_token_le if self.soap_user_type == "LE" else self.soap_token
        if self.use_soap and token_to_use:
            self.soap_client = EISSOAPClient(
                token=token_to_use,
                user_type=self.soap_user_type
            )
        else:
            self.soap_client = None
        
        # Базовые URL
        if self.use_mobile_api:
            # Мобильное API (может требовать авторизацию)
            self.api_url = "https://zakupki.gov.ru/epz/api/mobile/proxy"
        else:
            # Партнерский API (если существует)
            self.api_url = settings.EIS_API_URL or "https://zakupki.gov.ru/epz/api/partner/v1"
        
        # Базовый URL для HTML парсинга
        self.html_base_url = os.getenv("EIS_BASE_URL", "https://zakupki.gov.ru/epz/order/extendedsearch/results.html")
        
        self.api_key = settings.EIS_API_KEY
        self.cert_path = settings.EIS_CERT_PATH
        self.key_path = settings.EIS_KEY_PATH
        
        # Настройка SSL для работы с ЭЦП (только для партнерского API)
        self.ssl_context = None
        self.client_cert = None
        
        if not self.use_mobile_api and self.cert_path and self.key_path:
            if Path(self.cert_path).exists() and Path(self.key_path).exists():
                try:
                    # Настройка SSL контекста с клиентским сертификатом
                    self.ssl_context = ssl.create_default_context(cafile=certifi.where())
                    self.client_cert = (self.cert_path, self.key_path)
                    logger.info("ЭЦП сертификаты загружены")
                except Exception as e:
                    logger.warning(f"Ошибка загрузки ЭЦП: {e}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        Выполнить запрос к API ЕИС
        
        Поддерживает мобильное API (без ЭЦП) и партнерское API (с ЭЦП)
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Для мобильного API добавляем специфичные заголовки
        if self.use_mobile_api:
            headers["X-Requested-With"] = "XMLHttpRequest"
        
        try:
            # Создаём SSL контекст с клиентским сертификатом (если есть)
            ssl_ctx = None
            if self.client_cert and self.ssl_context:
                ssl_ctx = self.ssl_context
                # Загружаем клиентский сертификат в контекст
                try:
                    ssl_ctx.load_cert_chain(self.client_cert[0], self.client_cert[1])
                except Exception as e:
                    logger.warning(f"Could not load client certificate: {e}")
                    ssl_ctx = None
            
            connector = aiohttp.TCPConnector(ssl=ssl_ctx) if ssl_ctx else None
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    ssl=ssl_ctx if not connector else None
                ) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except Exception as e:
                            logger.error(f"Error parsing JSON response: {e}")
                            text = await response.text()
                            logger.debug(f"Response text: {text[:500]}")
                            return {}
                    else:
                        error_text = await response.text()
                        logger.error(f"EIS API error {response.status}: {error_text[:500]}")
                        return {}
        except aiohttp.ClientError as e:
            logger.error(f"Network error making request to EIS API: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error making request to EIS API: {e}")
            return {}
    
    async def search_tenders(
        self,
        filters: "TenderFilter"
    ) -> Dict:
        """
        Поиск тендеров по фильтрам
        
        Приоритет: SOAP API > HTML парсинг
        """
        # Приоритет 1: API (Mobile/Partner)
        if self.use_mobile_api:
            endpoint = "/search"
            params = {
                "pageNumber": filters.page,
                "recordsPerPage": filters.page_size
            }
            
            # Маппинг фильтров в API
            if filters.price_from:
                params["priceFrom"] = int(filters.price_from)
            if filters.price_to:
                params["priceTo"] = int(filters.price_to)
            if filters.date_from:
                params["publishDateFrom"] = filters.date_from.strftime("%Y-%m-%d")
            if filters.date_to:
                params["publishDateTo"] = filters.date_to.strftime("%Y-%m-%d")
            if filters.fz44:
                params["fz44"] = True
            if filters.fz223:
                params["fz223"] = True
            if filters.query:
                params["searchString"] = filters.query
            if filters.customer_inn:
                params["customerInn"] = filters.customer_inn
            if filters.region:
                params["regionCode"] = filters.region
            
            result = await self._make_request("GET", endpoint, params=params)
            
            if result:
                if result.get("items"):
                    return result
                elif isinstance(result, list):
                    return {"items": result, "total": len(result), "pageNumber": filters.page}
                elif "data" in result:
                    return {"items": result["data"], "total": result.get("total", 0), "pageNumber": filters.page}
        
        # Fallback: HTML Parsing
        if self.use_html_parsing:
             return await self._search_via_html(filters)
        
        return {"items": [], "total": 0, "pageNumber": filters.page}

    def _apply_advanced_filters(self, tender: Dict, filters: "TenderFilter") -> bool:
        """Применение сложных фильтров (пост-фильтрация)"""
        # Текстовый поиск (query)
        if filters.query:
            text = (tender.get("title", "") + " " + (tender.get("description") or "")).lower()
            query_lower = filters.query.lower()
            if query_lower not in text:
                return False
        
        # Текстовый поиск (Keywords)
        if filters.keywords:
            text = (tender.get("title", "") + " " + (tender.get("description") or "")).lower()
            if not all(k.lower() in text for k in filters.keywords):
                return False
        
        # Исключение слов
        if filters.exclude_words:
            text = (tender.get("title", "") + " " + (tender.get("description") or "")).lower()
            if any(w.lower() in text for w in filters.exclude_words):
                return False
        
        # Регион - фильтрация по региону заказчика
        # ВАЖНО: URL-фильтры ЕИС (customerRegionCodes) НЕ работают надежно!
        # Поэтому применяем строгую постфильтрацию на бэкенде
        if filters.region:
            tender_region = tender.get("customer_region") or tender.get("region") or tender.get("customerRegion")
            customer_name = tender.get("customer_name") or tender.get("customerName") or ""
            customer_address = tender.get("customer_address") or tender.get("address") or ""
            
            filter_region_lower = filters.region.lower()
            
            # Расширенный маппинг регионов (название -> код и ключевые слова)
            region_data = {
                "санкт-петербург": {"code": "78", "keywords": ["санкт-петербург", "петербург", "ленинград", "спб", "с.-петербург", "с-петербург", "г. санкт"]},
                "москва": {"code": "77", "keywords": ["москва", "московск", "г. москва", "город москва"]},
                "московская область": {"code": "50", "keywords": ["московской области", "подмосковье", "мо ", "московская обл"]},
                "ленинградская область": {"code": "47", "keywords": ["ленинградской области", "ленобласть", "ленинградская обл"]},
                "краснодарский край": {"code": "23", "keywords": ["краснодарск", "краснодар", "кубань"]},
                "свердловская область": {"code": "66", "keywords": ["свердловск", "екатеринбург"]},
                "тюменская область": {"code": "72", "keywords": ["тюмень", "тюменск"]},
                "новосибирская область": {"code": "54", "keywords": ["новосибирск"]},
                "татарстан": {"code": "16", "keywords": ["татарстан", "казань"]},
                "приморский край": {"code": "25", "keywords": ["приморск", "владивосток"]},
                "нижегородская область": {"code": "52", "keywords": ["нижегород", "нижний новгород"]},
                "самарская область": {"code": "63", "keywords": ["самар", "тольятти"]},
                "ростовская область": {"code": "61", "keywords": ["ростов", "ростовск"]},
                "воронежская область": {"code": "36", "keywords": ["воронеж"]},
                "челябинская область": {"code": "74", "keywords": ["челябинск"]},
                "пермский край": {"code": "59", "keywords": ["пермь", "пермск"]},
                "красноярский край": {"code": "24", "keywords": ["красноярск"]},
                "омская область": {"code": "55", "keywords": ["омск"]},
                "башкортостан": {"code": "02", "keywords": ["башкортостан", "башкирия", "уфа"]},
                "дагестан": {"code": "05", "keywords": ["дагестан", "махачкала"]},
            }
            
            # Получаем данные для выбранного региона. Фронтенд и SOAP могут
            # передавать как название ("Москва"), так и код субъекта ("77").
            region_info = region_data.get(filter_region_lower)
            if region_info is None:
                normalized_region_code = filter_region_lower.zfill(2) if filter_region_lower.isdigit() else filter_region_lower
                region_info = next(
                    (info for info in region_data.values() if info.get("code") == normalized_region_code),
                    {"code": normalized_region_code if filter_region_lower.isdigit() else None, "keywords": [filter_region_lower]},
                )
            keywords = region_info["keywords"]
            region_code = region_info["code"]
            
            # Собираем весь текст для поиска
            search_text = f"{customer_name} {customer_address} {tender_region or ''}".lower()
            
            # Если регион указан в тендере - проверяем соответствие
            if tender_region:
                tender_region_lower = str(tender_region).lower()
                # Проверяем по ключевым словам или коду
                region_match = any(kw in tender_region_lower for kw in keywords)
                if region_code:
                    region_match = region_match or region_code in str(tender_region)
                if region_match:
                    return True  # Регион совпадает
                # Регион указан, но НЕ совпадает - исключаем
                return False
            
            # Регион НЕ указан - проверяем по названию заказчика и адресу
            if any(kw in search_text for kw in keywords):
                return True  # Нашли ключевые слова региона
            
            # НЕ нашли никаких признаков нужного региона - ИСКЛЮЧАЕМ тендер
            # (URL-фильтры ЕИС не работают, поэтому нужна строгая фильтрация)
            logger.debug(f"Region filter excluded tender: {tender.get('number')} - no match for '{filters.region}' in '{search_text[:100]}'")
            return False
        
        # Цена
        if filters.price_from and tender.get("initial_price"):
            try:
                if float(tender["initial_price"]) < float(filters.price_from):
                    return False
            except (ValueError, TypeError):
                pass
        if filters.price_to and tender.get("initial_price"):
            try:
                if float(tender["initial_price"]) > float(filters.price_to):
                    return False
            except (ValueError, TypeError):
                pass
                
        return True
    
    async def get_tender_details(self, tender_id: str) -> Dict:
        """
        Получить детальную информацию о тендере
        
        Парсит HTML страницу тендера с zakupki.gov.ru для извлечения всех полей
        """
        # Парсим HTML страницу тендера
        try:
            detail_url = f"https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber={tender_id}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(detail_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_tender_detail_page(html, tender_id)
                    else:
                        logger.warning(f"Error fetching tender details: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error getting tender details: {e}")
            return {}
    
    def _parse_tender_detail_page(self, html: str, tender_id: str) -> Dict:
        """Парсит детальную HTML страницу тендера с zakupki.gov.ru"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            all_text = soup.get_text()
            tender_data = {
                'id': tender_id,
                'eis_id': tender_id,
                'number': tender_id,
                'documents': [],
                'requirements': {},
                'preferences': [],
                'status': 'active'
            }
            
            # 1. Название тендера
            title_elem = (
                soup.find('h1', class_=re.compile(r'pageTitle|title|registry-entry__title')) or
                soup.find('span', class_=re.compile(r'cardMainInfo__purchaseObject')) or
                soup.find('div', class_=re.compile(r'cardMainInfo__content'))
            )
            if title_elem:
                tender_data['title'] = title_elem.get_text(strip=True)
                tender_data['purchaseObjectInfo'] = tender_data['title']

            # 2. Цена и валюта
            price_elem = soup.find('span', class_=re.compile(r'price|cost|amount')) or \
                         soup.find('div', class_=re.compile(r'price-block__value|price'))
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Очистка цены (оставляем только цифры и разделители)
                price_val = re.sub(r'[^\d\.,]', '', price_text).replace(',', '.')
                if price_val:
                    try:
                        tender_data['initial_price'] = float(price_val)
                    except: pass
                
                if '₽' in price_text or 'руб' in price_text.lower():
                    tender_data['currency'] = 'RUB'

            # 3. Заказчик (ИНН, Название)
            customer_match = re.search(r'ИНН\s*[:]?\s*(\d{10,12})', all_text)
            if customer_match:
                tender_data['customer_inn'] = customer_match.group(1)
            
            customer_elem = soup.find('a', href=re.compile(r'customer-info')) or \
                            soup.find(string=re.compile(r'Организация, осуществляющая размещение', re.I))
            if customer_elem:
                if customer_elem.name == 'a':
                    tender_data['customer_name'] = customer_elem.get_text(strip=True)
                else:
                    # Ищем следующее значение
                    val = customer_elem.find_next(['div', 'span', 'td'])
                    if val:
                        tender_data['customer_name'] = val.get_text(strip=True)

            # 4. Регион
            region_match = re.search(r'Место\s+нахождения\s+заказчика[^-]+-\s*([А-Яа-яё\s]+(?:область|край|республика|г\.\s*[А-Яа-яё]+))', all_text, re.I)
            if region_match:
                tender_data['customer_region'] = region_match.group(1).strip()
            else:
                # Паттерн для поиска в адресе
                addr_match = re.search(r'\d{6},\s*([А-Яа-яё\s]+(?:область|край|республика|г\.\s*[А-Яа-яё]+))', all_text)
                if addr_match:
                    tender_data['customer_region'] = addr_match.group(1).strip()

            # 5. Статус
            status_elem = soup.find('div', class_=re.compile(r'cardMainInfo__state'))
            if status_elem:
                tender_data['status'] = status_elem.get_text(strip=True)

            # 6. Аванс (Prepayment)
            if re.search(r'аванс\s+предусмотрен|предусмотрен\s+аванс|выплата\s+аванса', all_text, re.I):
                advance_percent = re.search(r'аванс[^-]+-\s*(\d+(?:[\.,]\d+)?)%', all_text, re.I)
                tender_data['prepayment_type'] = f"Предусмотрен аванс {advance_percent.group(1)}%" if advance_percent else "Предусмотрен аванс"
            else:
                tender_data['prepayment_type'] = "Без аванса"

            # 7. Преимущества (Preferences)
            pref_labels = soup.find_all(string=re.compile(r'Преимущества|Ограничения', re.I))
            for label in pref_labels:
                val_elem = label.find_next(['td', 'div', 'span'])
                if val_elem:
                    val_text = val_elem.get_text(strip=True)
                    if val_text and len(val_text) > 3 and val_text not in tender_data['preferences']:
                        tender_data['preferences'].append(val_text)

            # 8. Даты
            pub_date = re.search(r'Размещено\s*[:]?\s*(\d{2}\.\d{2}\.\d{4})', all_text)
            if pub_date:
                tender_data['publication_date'] = pub_date.group(1)
            
            deadline = re.search(r'окончания\s+подачи\s+заявок\s*[:]?\s*(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})', all_text, re.I)
            if deadline:
                tender_data['application_deadline'] = deadline.group(1)

            # 9. Ссылка на документы
            doc_link = soup.find('a', href=re.compile(r'documents\.html')) or \
                       soup.find('a', string=re.compile(r'Документы', re.I))
            if doc_link:
                href = doc_link.get('href', '')
                tender_data['documents_url'] = href if href.startswith('http') else f"https://zakupki.gov.ru{href}"

            return tender_data
        except Exception as e:
            logger.error(f"Error parsing tender detail page: {e}")
            return {'id': tender_id, 'eis_id': tender_id, 'status': 'active'}
            
        except Exception as e:
            logger.error(f"Error parsing tender detail page: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {'id': tender_id, 'eis_id': tender_id}
    
    async def get_tender_documents(self, tender_id: str) -> List[Dict]:
        """Получить список документов тендера"""
        if self.use_mobile_api:
            endpoint = f"/view/{tender_id}/documents"
        else:
            endpoint = f"/tenders/{tender_id}/documents"
        
        response = await self._make_request("GET", endpoint)
        
        # Нормализуем ответ
        if isinstance(response, list):
            return response
        elif isinstance(response, dict):
            return response.get("documents", response.get("items", []))
        return []
    
    async def download_document(self, document_url: str) -> bytes:
        """Скачать документ по URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(document_url, ssl=self.ssl_context) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Error downloading document: {response.status}")
                        return b""
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return b""
    
    def parse_tender_data(self, raw_data: Dict) -> Dict:
        """
        Парсинг данных тендера из ответа API в наш формат
        """
        # Обрабатываем требования - могут быть списком строк или словарем
        requirements = raw_data.get("requirements", {})
        if isinstance(requirements, list):
            # Преобразуем список требований в словарь для удобства
            requirements = {"list": requirements}
        elif not isinstance(requirements, dict):
            requirements = {}
        
        return {
            "eis_id": raw_data.get("id") or raw_data.get("number") or raw_data.get("eis_id"),
            "number": raw_data.get("number") or raw_data.get("id"),
            "title": raw_data.get("purchaseObjectInfo") or raw_data.get("title"),
            "description": raw_data.get("description"),
            "customer_name": raw_data.get("customer", {}).get("fullName") if isinstance(raw_data.get("customer"), dict) else raw_data.get("customerName"),
            "customer_inn": raw_data.get("customer", {}).get("inn") if isinstance(raw_data.get("customer"), dict) else raw_data.get("customerInn"),
            "customer_region": (
                raw_data.get("customer", {}).get("region") 
                if isinstance(raw_data.get("customer"), dict) 
                else raw_data.get("customerRegion") or raw_data.get("region")
            ),
            "initial_price": raw_data.get("price") or raw_data.get("initialPrice"),
            "currency": raw_data.get("currency", "RUB"),
            "guarantee_amount": raw_data.get("applicationGuarantee"),
            "contract_guarantee": raw_data.get("contractGuarantee"),
            "publication_date": self._parse_date(raw_data.get("publishDate") or raw_data.get("publicationDate")),
            "application_deadline": self._parse_date(raw_data.get("applicationDeadline") or raw_data.get("deadline")),
            "contract_deadline": self._parse_date(raw_data.get("contractDeadline") or raw_data.get("biddingDate") or raw_data.get("summarizingDate")),
            "status": raw_data.get("status", "active"),
            "procedure_type": raw_data.get("procedureType") or raw_data.get("procedure") or raw_data.get("procedureCode"),
            "documents_url": raw_data.get("documentsUrl") or raw_data.get("href"),
            "documents_data": raw_data.get("documents") or raw_data.get("documents_data", []),
            "okpd2_codes": raw_data.get("okpd2Codes") or raw_data.get("okpd2_codes", []),
            "requirements": requirements
        }
    
    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Парсинг даты из различных форматов"""
        if not date_str:
            return None
        
        # Удаляем таймзону для парсинга (сохраняем только дату и время)
        date_str_clean = date_str.split('+')[0].split('-')[0] if '+' in date_str or (date_str.count('-') > 2) else date_str
        
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str_clean, fmt)
            except ValueError:
                continue
        
        return None
    
    async def search_tenders(self, filters: "TenderFilter") -> Dict:
        """
        Поиск тендеров с учетом приоритета источников
        Приоритет: SOAP API > HTML парсинг
        """
        logger.debug(f"Entering search_tenders. use_soap={self.use_soap}, soap_client={self.soap_client is not None}, use_html={self.use_html_parsing}")
        
        try:
            # Приоритет 1: SOAP API (официальный способ с токеном)
            # ⚠️ Если токен заблокирован/недействителен, пропускаем SOAP и сразу используем HTML
            if self.use_soap and self.soap_client:
                try:
                    logger.info("Attempting SOAP API search")
                    # Преобразуем фильтры для SOAP API
                    region_code = None
                    if filters.region:
                        # Маппинг регионов (названия -> коды)
                        region_map = {
                            "Москва": "77",
                            "Санкт-Петербург": "78", 
                            "Московская область": "50",
                            "Ленинградская область": "47",
                        }
                        region_code = region_map.get(filters.region, filters.region)
                    
                    # Вызываем SOAP API
                    soap_results = await self.soap_client.search_tenders(
                        region=region_code,
                        limit=filters.page_size
                    )
                    
                    if soap_results and len(soap_results) > 0:
                        # Преобразуем результаты SOAP в формат для UI
                        items = []
                        for soap_item in soap_results:
                            # Маппинг полей из SOAP формата
                            mapped_item = self.parse_tender_data(soap_item)
                            if mapped_item:
                                # Применяем фильтры
                                if self._apply_advanced_filters(mapped_item, filters):
                                    items.append(mapped_item)
                        
                        logger.info(f"SOAP API returned {len(items)} tenders after filtering (from {len(soap_results)} raw)")
                        return {
                            "items": items,
                            "total": len(items),
                            "page": filters.page,
                            "pages": 1
                        }
                    else:
                        logger.warning("SOAP API returned empty results (токен может быть заблокирован), используем HTML парсинг")
                except Exception as e:
                    error_msg = str(e)
                    if "Токены для сервисов отдачи отсутствуют" in error_msg or "code: 5" in error_msg:
                        logger.warning(f"⚠️ SOAP токен заблокирован или недействителен: {error_msg}. Используем HTML парсинг.")
                    else:
                        logger.warning(f"SOAP API method failed: {e}, trying fallback")
                    import traceback
                    logger.debug(traceback.format_exc())
            
            # Приоритет 2: HTML парсинг (fallback) - ВСЕГДА используем как fallback
            # Если SOAP не работает, HTML парсинг - единственный способ получить данные
            logger.info("Using HTML parsing as fallback (SOAP failed or unavailable)")
            logger.info(f"HTML parsing filters: region={filters.region}, query={filters.query}, page={filters.page}, page_size={filters.page_size}")
            result = await self._search_via_html(filters)
            logger.info(f"HTML parsing returned: {len(result.get('items', []))} items, total={result.get('total', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"Error in search_tenders: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {"items": [], "total": 0, "page": 1, "pages": 0}

    async def _search_via_html(
        self,
        filters: "TenderFilter"
    ) -> Dict:
        """
        Парсинг HTML страниц ЕИС - основной метод получения данных
        
        Парсит публичные страницы поиска закупок
        """
        try:
            # Формируем параметры для поиска
            # Увеличиваем page_size для HTML парсинга (ЕИС поддерживает до 500 на странице)
            # Для Live Search используем запрошенный page_size от фронтенда, но не меньше 100
            # Если фронтенд запрашивает больше 100, используем его значение (до максимума 500)
            html_page_size = max(100, min(filters.page_size or 100, 500))  # От 100 до 500
            
            params = {
                "pageNumber": filters.page,
                "recordsPerPage": f"_{html_page_size}", # ЕИС любит _50, _100, _500
                "morphology": "on",
                "search-filter": "Дате+размещения",
                "sortBy": "BY_RELEVANCE_DESC"
            }
            
            # Добавляем фильтры
            
            # Маппинг регионов (названия -> коды субъектов РФ)
            # В ЕИС используются коды ОКАТО/ОКТМО или просто коды регионов
            region_map = {
                "Адыгея": "01", "Алтай": "04", "Алтайский край": "22", "Амурская область": "28",
                "Архангельская область": "29", "Астраханская область": "30", "Башкортостан": "02",
                "Белгородская область": "31", "Брянская область": "32", "Бурятия": "03",
                "Владимирская область": "33", "Волгоградская область": "34", "Вологодская область": "35",
                "Воронежская область": "36", "Дагестан": "05", "Еврейская АО": "79",
                "Забайкальский край": "75", "Ивановская область": "37", "Ингушетия": "06",
                "Иркутская область": "38", "Кабардино-Балкария": "07", "Калининградская область": "39",
                "Калмыкия": "08", "Калужская область": "40", "Камчатский край": "41",
                "Карачаево-Черкесия": "09", "Карелия": "10", "Кемеровская область": "42",
                "Кировская область": "43", "Коми": "11", "Костромская область": "44",
                "Краснодарский край": "23", "Красноярский край": "24", "Крым": "91",
                "Курганская область": "45", "Курская область": "46", "Ленинградская область": "47",
                "Липецкая область": "48", "Магаданская область": "49", "Марий Эл": "12",
                "Мордовия": "13", "Москва": "77", "Московская область": "50",
                "Мурманская область": "51", "Ненецкий АО": "83", "Нижегородская область": "52",
                "Новгородская область": "53", "Новосибирская область": "54", "Омская область": "55",
                "Оренбургская область": "56", "Орловская область": "57", "Пензенская область": "58",
                "Пермский край": "59", "Приморский край": "25", "Псковская область": "60",
                "Республика Алтай": "04", "Республика Башкортостан": "02", "Республика Бурятия": "03",
                "Республика Дагестан": "05", "Республика Ингушетия": "06", "Республика Калмыкия": "08",
                "Республика Карелия": "10", "Республика Коми": "11", "Республика Крым": "91",
                "Республика Марий Эл": "12", "Республика Мордовия": "13", "Республика Саха (Якутия)": "14",
                "Республика Северная Осетия — Алания": "15", "Республика Татарстан": "16",
                "Республика Тыва": "17", "Республика Хакасия": "19", "Ростовская область": "61",
                "Рязанская область": "62", "Самарская область": "63", "Санкт-Петербург": "78",
                "Саратовская область": "64", "Сахалинская область": "65", "Свердловская область": "66",
                "Севастополь": "92", "Смоленская область": "67", "Ставропольский край": "26",
                "Тамбовская область": "68", "Татарстан": "16", "Тверская область": "69",
                "Томская область": "70", "Тульская область": "71", "Тыва": "17",
                "Тюменская область": "72", "Удмуртия": "18", "Ульяновская область": "73",
                "Хабаровский край": "27", "Хакасия": "19", "Ханты-Мансийский АО — Югра": "86",
                "Челябинская область": "74", "Чечня": "20", "Чувашия": "21",
                "Чукотский АО": "87", "Ямало-Ненецкий АО": "89", "Ярославская область": "76"
            }
            
            search_query = filters.query or ""
            if filters.exclude_words:
                for word in filters.exclude_words:
                    if word.strip():
                        search_query += f" -{word.strip()}"
            
            if search_query:
                params["searchString"] = search_query.strip()
            
            # ОКПД2
            if filters.okpd2:
                params["okpd2Code"] = filters.okpd2
            elif filters.okpd2_codes and len(filters.okpd2_codes) > 0:
                # В HTML поиске обычно передается один код или через фильтр
                params["okpd2Code"] = filters.okpd2_codes[0]

            # Регион (Место поставки / Регион заказчика)
            reg_val = filters.region
            if not reg_val and filters.regions and len(filters.regions) > 0:
                reg_val = filters.regions[0]
                
            if reg_val:
                # Преобразуем название в код
                code = region_map.get(str(reg_val), str(reg_val))
                # Используем правильный параметр ЕИС для фильтрации по региону заказчика
                # customerRegionCodes - регион заказчика (работает!)
                # customerPlaceCodes - место поставки (может не работать для всех закупок)
                params["customerRegionCodes"] = code
                # Также пробуем deliveryRegionCodes для места поставки
                params["deliveryRegionCodes"] = code

            # Статусы (Этапы)
            # af - Подача заявок
            # ca - Работа комиссии
            # pc - Прием заявок завершен
            # pa - Заключение контракта
            # pl - Размещение завершено
            if filters.status:
                s = filters.status.lower()
                if s == 'active' or 'подача' in s:
                    # ТОЛЬКО подача заявок, без работы комиссии
                    params["af"] = "on"
                    # Явно убираем ca, если он был установлен ранее
                    if "ca" in params:
                        del params["ca"]
                elif s == 'evaluation' or 'комиссия' in s:
                    params["ca"] = "on"
                    params["pc"] = "on"
                    # Убираем af, если был установлен
                    if "af" in params:
                        del params["af"]
                elif s == 'completed' or 'завершено' in s:
                    params["pl"] = "on"
                    # Убираем активные статусы
                    if "af" in params:
                        del params["af"]
                    if "ca" in params:
                        del params["ca"]
                elif s == 'cancelled' or 'отменено' in s:
                    # В ЕИС нет единого флага отмены в URL, но можно исключить активные
                    pass
            else:
                # По умолчанию ищем активные (подача заявок) И работу комиссии
                params["af"] = "on"
                params["ca"] = "on"

            if filters.price_from:
                params["priceFromGeneral"] = str(filters.price_from)
            if filters.price_to:
                params["priceToGeneral"] = str(filters.price_to)
            if filters.date_from:
                params["publishDateFrom"] = filters.date_from.strftime("%d.%m.%Y")
            if filters.date_to:
                params["publishDateTo"] = filters.date_to.strftime("%d.%m.%Y")
            
            # ФЗ
            params["fz44"] = "on" if filters.fz44 else "off"
            params["fz223"] = "on" if filters.fz223 else "off"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            logger.info(f"Generated HTML search params: {params}")
            
            # Создаем SSL контекст без проверки сертификатов (для разработки)
            # В production нужно использовать правильные сертификаты
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                async with session.get(self.html_base_url, params=params) as response:
                    logger.info(f"Search URL: {response.url}")
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        items = []
                        
                        # Парсим карточки тендеров
                        # Структура может меняться, нужно адаптировать под реальную HTML
                        # Пробуем разные селекторы
                        tender_cards = []
                        
                        # Вариант 1: поиск по классу
                        cards1 = soup.find_all('div', class_='search-registry-entry-block')
                        if cards1:
                            tender_cards.extend(cards1)
                            logger.debug(f"Found {len(cards1)} cards by class 'search-registry-entry-block'")
                        
                        # Вариант 2: поиск по data-id
                        if not tender_cards:
                            cards2 = soup.find_all('div', {'data-id': True})
                            if cards2:
                                tender_cards.extend(cards2)
                                logger.debug(f"Found {len(cards2)} cards by data-id")
                        
                        # Вариант 3: поиск по tr с классом
                        if not tender_cards:
                            cards3 = soup.find_all('tr', class_='search-registry-entry')
                            if cards3:
                                tender_cards.extend(cards3)
                                logger.debug(f"Found {len(cards3)} cards by tr.search-registry-entry")
                        
                        # Вариант 4: поиск по другим возможным селекторам
                        if not tender_cards:
                            # Пробуем найти любые div с классом содержащим "registry" или "tender"
                            cards4 = soup.find_all('div', class_=lambda x: x and ('registry' in x.lower() or 'tender' in x.lower() or 'order' in x.lower()))
                            if cards4:
                                tender_cards.extend(cards4)
                                logger.debug(f"Found {len(cards4)} cards by registry/tender/order class")
                        
                        # Вариант 5: поиск по ссылкам на тендеры
                        if not tender_cards:
                            links = soup.find_all('a', href=re.compile(r'regNumber|view.*order|notice'))
                            if links:
                                # Берем родительские элементы ссылок
                                for link in links[:filters.page_size]:
                                    parent = link.find_parent(['div', 'tr', 'li'])
                                    if parent and parent not in tender_cards:
                                        tender_cards.append(parent)
                                logger.debug(f"Found {len(tender_cards)} cards by links")
                        
                        logger.info(f"Total found {len(tender_cards)} tender cards to parse")
                        
                        if not tender_cards:
                            # Сохраняем HTML для отладки
                            logger.warning("No tender cards found! Saving HTML for debugging...")
                            html_sample = html[:5000] if len(html) > 5000 else html
                            logger.debug(f"HTML sample (first 5000 chars): {html_sample}")
                        
                        # Парсим все найденные карточки (до html_page_size), но возвращаем только запрошенное количество
                        for idx, card in enumerate(tender_cards[:html_page_size]):
                            try:
                                item = self._parse_tender_card(card)
                                if item:
                                    # Логируем что удалось извлечь
                                    extracted_fields = []
                                    if item.get('title'): extracted_fields.append('title')
                                    if item.get('price') or item.get('initial_price'): extracted_fields.append('price')
                                    if item.get('publishDate') or item.get('publication_date'): extracted_fields.append('date')
                                    if item.get('customerName'): extracted_fields.append('customer')
                                    logger.debug(f"Card {idx+1}: extracted {', '.join(extracted_fields) if extracted_fields else 'only id/title'}")
                                    items.append(item)
                                else:
                                    logger.debug(f"Card {idx+1}: failed to parse (no id/title found)")
                            except Exception as e:
                                logger.debug(f"Error parsing card {idx+1}: {e}")
                                continue
                        
                        # Пытаемся найти общее количество - улучшенный поиск
                        total = 0
                        
                        # Вариант 1: поиск по классу search-results-count
                        total_elem = (
                            soup.find('span', class_='search-results-count') or
                            soup.find('div', class_='search-results-count') or
                            soup.find('span', class_=re.compile(r'count|total|results')) or
                            soup.find('div', class_=re.compile(r'count|total|results'))
                        )
                        
                        if total_elem:
                            text = total_elem.get_text(strip=True)
                            # Извлекаем число из текста типа "Найдено: 1234", "Всего: 1234", "1234 результатов"
                            numbers = re.findall(r'\d+', text.replace(' ', ''))
                            if numbers:
                                # Берем самое большое число (это обычно общее количество)
                                total = max([int(n) for n in numbers])
                        
                        # Вариант 2: поиск в тексте страницы
                        if total == 0:
                            page_text = soup.get_text()
                            # Ищем паттерны типа "Найдено 1234", "Всего найдено 1234", "1234 закупок"
                            total_matches = re.findall(r'(?:найдено|всего|закупок|тендеров|извещений)[\s:]*(\d+)', page_text, re.I)
                            if total_matches:
                                total = max([int(n) for n in total_matches])
                        
                        # Вариант 3: поиск в пагинации (если есть информация о количестве страниц)
                        if total == 0:
                            pagination = soup.find('div', class_=re.compile(r'pagination|pages'))
                            if pagination:
                                pagination_text = pagination.get_text()
                                # Ищем числа в пагинации
                                pagination_numbers = re.findall(r'\d+', pagination_text)
                                if pagination_numbers:
                                    # Если есть информация о страницах, умножаем на размер страницы
                                    max_page = max([int(n) for n in pagination_numbers if int(n) > 0 and int(n) < 10000])
                                    if max_page > filters.page:
                                        total = max_page * html_page_size  # Приблизительная оценка
                        
                        # ВАЖНО: Пост-фильтрация применяется для всех фильтров
                        # URL-параметры ЕИС (customerRegionCodes, af, ca и т.д.) не всегда работают надежно
                        # Поэтому применяем все фильтры на бэкенде для гарантии результата
                        filtered_items = []
                        for item in items:
                            # Применяем все фильтры
                            if self._apply_advanced_filters(item, filters):
                                filtered_items.append(item)
                        
                        # Если после фильтрации количество изменилось, обновляем total
                        if len(filtered_items) != len(items):
                            logger.info(f"Applied post-filtering: {len(items)} -> {len(filtered_items)} items (only additional filters, region/status already in URL)")
                        
                        items = filtered_items
                        
                        # Пересчитываем total на основе отфильтрованных результатов
                        # Если применили дополнительную фильтрацию, используем количество отфильтрованных элементов
                        if len(filtered_items) < len(items):
                            # Если на странице полный набор отфильтрованных карточек, значит есть еще страницы
                            if len(filtered_items) == filters.page_size:
                                total = filters.page * filters.page_size + 1
                            else:
                                # Это последняя страница
                                total = (filters.page - 1) * filters.page_size + len(filtered_items)
                            logger.info(f"Recalculated total based on filtered items: {total} (filtered {len(items)} -> {len(filtered_items)})")
                        elif total == 0:
                            # Если не нашли общее количество из HTML, оцениваем по количеству карточек
                            if len(items) == html_page_size:
                                # Если на странице полный набор карточек, значит есть еще страницы
                                total = filters.page * html_page_size + 1
                                logger.warning(f"Could not parse total count, estimating: {total} (based on page {filters.page} with {len(items)} items)")
                            else:
                                # Если карточек меньше чем page_size, значит это последняя страница
                                total = (filters.page - 1) * html_page_size + len(items)
                                logger.info(f"Could not parse total count, estimating: {total} (last page with {len(items)} items)")
                        
                        # Возвращаем только запрошенное количество для текущей страницы
                        # Возвращаем все найденные элементы для текущей страницы
                        # Если html_page_size >= filters.page_size, возвращаем все items
                        # Иначе применяем пагинацию
                        if html_page_size >= filters.page_size:
                            # Возвращаем все найденные элементы (до html_page_size)
                            paginated_items = items[:filters.page_size] if len(items) > filters.page_size else items
                        else:
                            # Применяем пагинацию только если html_page_size меньше запрошенного
                            start_idx = (filters.page - 1) * filters.page_size
                            end_idx = start_idx + filters.page_size
                            paginated_items = items[start_idx:end_idx]
                        
                        logger.info(f"Parsed {len(items)} tenders from HTML (requested {html_page_size}), showing {len(paginated_items)} items for page {filters.page}, total estimated: {total}")
                        
                        return {
                            "items": paginated_items,
                            "total": total,
                            "page": filters.page,
                            "pages": (total + filters.page_size - 1) // filters.page_size if total > 0 and filters.page_size > 0 else 1,
                            "page_size": filters.page_size  # Возвращаем оригинальный page_size для фронтенда
                        }
                    else:
                        logger.error(f"HTTP error {response.status} when parsing HTML")
                        return {"items": [], "total": 0, "pageNumber": filters.page}
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return {"items": [], "total": 0, "pageNumber": filters.page}
    
    def _parse_tender_card(self, card) -> Optional[Dict]:
        """
        Парсит одну карточку тендера из HTML
        
        Адаптировано под реальную структуру HTML страницы ЕИС zakupki.gov.ru
        """
        try:
            item = {}
            
            # Ищем ссылку на тендер - разные варианты структуры
            link = card.find('a', href=re.compile(r'regNumber|view')) or \
                   card.find('a', class_=re.compile(r'registry|tender|order')) or \
                   card.find('a', href=True)
            
            if link:
                href = link.get('href', '')
                # Извлекаем ID из URL типа /epz/order/view/orderInfo.html?regNumber=...
                reg_match = re.search(r'regNumber=([^\u0026\"\'\s]+)', href)
                if reg_match:
                    item['id'] = reg_match.group(1)
                    item['number'] = reg_match.group(1)
                    item['eis_id'] = reg_match.group(1)
                item['url'] = href if href.startswith('http') else f"https://zakupki.gov.ru{href}"
            
            # Если ID не найден в URL, ищем в тексте карточки
            if 'id' not in item:
                # Ищем паттерн № 0000...
                # Обычно номер закупки находится в блоке с номером
                number_elem = card.find(text=re.compile(r'№\s*\d{11,20}'))
                if number_elem:
                    num_match = re.search(r'№\s*(\d{11,20})', number_elem)
                    if num_match:
                        item['id'] = num_match.group(1)
                        item['number'] = num_match.group(1)
                        item['eis_id'] = num_match.group(1)
                
                # Если все еще нет, ищем просто 19 цифр подряд (для 44-ФЗ) или 11 (для 223-ФЗ)
                if 'id' not in item:
                    text_content = card.get_text()
                    id_match = re.search(r'(?:№|бизнес-закупка)\s*(\d{11,20})', text_content, re.IGNORECASE)
                    if id_match:
                        item['id'] = id_match.group(1)
                        item['number'] = id_match.group(1)
                        item['eis_id'] = id_match.group(1)
            
            # Статус закупки (Этап закупки)
            status_text = None
            status_elem = card.find('div', class_=re.compile(r'header-mid__item|status|registry-entry__header-mid__item'))
            if status_elem:
                # В ЕИС статус часто в блоке с надписью "Статус" или в первом header-mid__item
                # Попробуем найти конкретно текст статуса
                inner_status = status_elem.find(class_=re.compile(r'status|value'))
                if inner_status:
                    status_text = inner_status.get_text(strip=True)
                else:
                    status_text = status_elem.get_text(strip=True).replace('Статус', '').strip()
            
            if not status_text:
                # Поиск по всему тексту карточки для ключевых фраз
                text_content = card.get_text().lower()
                if 'подача заявок' in text_content: status_text = 'Подача заявок'
                elif 'работа комиссии' in text_content: status_text = 'Работа комиссии'
                elif 'определение поставщика завершено' in text_content: status_text = 'Определение завершено'
                elif 'заключение контракта' in text_content: status_text = 'Заключение контракта'
                elif 'размещение отменено' in text_content: status_text = 'Размещение отменено'
                elif 'признана несостоявшейся' in text_content: status_text = 'Признана несостоявшейся'
                elif 'контракт заключен' in text_content or 'договор заключен' in text_content: status_text = 'Контракт заключен'
            
            if status_text:
                item['status'] = status_text
            else:
                item['status'] = 'active'
            
            # ОБЪЕКТ ЗАКУПКИ и СПОСОБ ЗАКУПКИ - ищем отдельно!
            # В карточке поиска может быть несколько элементов:
            # 1. Способ закупки (223-ФЗ, 44-ФЗ, Аукцион и т.д.)
            # 2. Объект закупки (что именно закупается)
            
            # Сначала ищем по явной метке "Объект закупки"
            object_label = card.find(string=re.compile(r'Объект\s+закупки', re.I))
            if object_label:
                parent = object_label.find_parent()
                if parent:
                    # Ищем текст объекта в том же блоке или соседнем
                    # В ЕИС это часто класс registry-entry__body-value
                    object_value = parent.find_next_sibling(class_=re.compile(r'body-value|value'))
                    if not object_value:
                        # Пробуем найти внутри родителя
                        object_value = parent.find_parent().find(class_=re.compile(r'body-value|value'))
                    
                    if object_value:
                        obj_text = object_value.get_text(strip=True)
                        if obj_text and len(obj_text) > 5:
                            item['purchaseObjectInfo'] = obj_text
                            item['title'] = obj_text

            # Если объект не найден по метке, ищем по ссылке-заголовку
            if 'purchaseObjectInfo' not in item:
                title_elem = (
                    card.find('a', class_=re.compile(r'title|name|registry-entry__title')) or
                    card.find('div', class_=re.compile(r'title|name|registry-entry__title')) or
                    card.find('span', class_=re.compile(r'title|name')) or
                    card.find('td', class_=re.compile(r'title|name')) or
                    (link if link else None)
                )
                
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text and len(title_text) > 5:
                        # Проверяем, является ли это способом закупки или статусом
                        is_skip_text = (
                            title_text.startswith('223-ФЗ') or 
                            title_text.startswith('44-ФЗ') or 
                            title_text.startswith('615 ПП РФ') or
                            'Закупка у единственного' in title_text or
                            'Аукцион' in title_text or
                            'Конкурс' in title_text or
                            'Запрос котировок' in title_text or
                            'Запрос предложений' in title_text or
                            'Определение поставщика завершено' in title_text or
                            'Определение поставщика (подрядчика, исполнителя) завершено' in title_text or
                            'Определение поставщика (подрядчика, исполнителя) приостановлено' in title_text
                        )
                        
                        if is_skip_text:
                            # Это способ закупки или статус, сохраняем как процедуру
                            item['procedureType'] = title_text
                            item['procedure_type'] = title_text
                            if 'title' not in item:
                                item['title'] = title_text
                        else:
                            # Это объект закупки
                            item['title'] = title_text
                            item['purchaseObjectInfo'] = title_text
            
            # Если всё еще не нашли объект закупки, ищем его в других местах карточки по длине и отсутствию стоп-слов
            if 'purchaseObjectInfo' not in item or not item.get('purchaseObjectInfo'):
                all_text_elements = card.find_all(['div', 'span', 'td', 'p'], string=True)
                for elem in all_text_elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 20:
                        if not (
                            text.startswith('223-ФЗ') or 
                            text.startswith('44-ФЗ') or 
                            'Закупка у единственного' in text or
                            'Аукцион' in text or
                            'Конкурс' in text or
                            'Определение поставщика' in text or
                            text.startswith('№') or
                            'Опубликовано' in text or
                            'До ' in text or
                            '₽' in text or
                            'ИНН' in text
                        ):
                            item['purchaseObjectInfo'] = text
                            if 'title' not in item or item.get('title') in ['Определение поставщика завершено', '44-ФЗ', '223-ФЗ']:
                                item['title'] = text
                            break
            
            # Цена - ищем в разных местах (улучшенный поиск)
            price_text = None
            
            # Вариант 1: поиск по классу
            price_elem = (
                card.find('div', class_=re.compile(r'price|amount|cost|sum')) or
                card.find('span', class_=re.compile(r'price|amount|cost|sum')) or
                card.find('td', class_=re.compile(r'price|amount|cost|sum')) or
                card.find('p', class_=re.compile(r'price|amount|cost|sum'))
            )
            
            if price_elem:
                if price_elem.name == 'td' and price_elem.find_next('td'):
                    price_text = price_elem.find_next('td').get_text(strip=True)
                else:
                    price_text = price_elem.get_text(strip=True)
            
            # Вариант 2: поиск по тексту "цена", "стоимость", "НМЦК"
            if not price_text:
                price_label = card.find(string=re.compile(r'цена|стоимость|НМЦК|начальная\s+макс', re.I))
                if price_label:
                    parent = price_label.find_parent()
                    if parent:
                        # Ищем число в том же элементе или соседних
                        price_text = parent.get_text(strip=True)
                        # Также проверяем следующий элемент
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            next_text = next_elem.get_text(strip=True)
                            if re.search(r'\d', next_text):
                                price_text = next_text
            
            # Вариант 3: поиск чисел с валютой (₽, руб, руб.)
            if not price_text:
                text_content = card.get_text()
                # Ищем паттерн: число + пробел + валюта
                price_match = re.search(r'(\d[\d\s,\.]+)\s*(?:₽|руб|руб\.|RUB)', text_content, re.I)
                if price_match:
                    price_text = price_match.group(1)
            
            # Извлекаем число из найденного текста
            if price_text:
                # Удаляем все кроме цифр, точек и запятых
                price_clean = re.sub(r'[^\d,\.]', '', price_text.replace(' ', ''))
                # Заменяем запятую на точку
                price_clean = price_clean.replace(',', '.')
                # Извлекаем число
                price_match = re.search(r'(\d+\.?\d*)', price_clean)
                if price_match:
                    try:
                        price_value = float(price_match.group(1))
                        # Если число меньше 1000, возможно это в тысячах или миллионах
                        # Но пока оставляем как есть
                        item['price'] = price_value
                        item['initialPrice'] = price_value
                        item['initial_price'] = price_value
                    except (ValueError, AttributeError):
                        pass
            
            # Заказчик - ищем в разных местах (улучшено)
            customer_text = None
            customer_inn = None
            
            customer_elem = (
                card.find('div', class_=re.compile(r'customer|organization|zakazchik|registry-entry__body-href')) or
                card.find('a', class_=re.compile(r'customer|organization|registry-entry__body-href')) or
                card.find('span', class_=re.compile(r'customer|organization')) or
                card.find('td', class_=re.compile(r'customer|organization'))
            )
            
            if customer_elem:
                customer_text = customer_elem.get_text(strip=True)
            
            # Если не нашли по классу, ищем по тексту заголовка "Заказчик"
            if not customer_text:
                customer_label = card.find(string=re.compile(r'заказчик', re.I))
                if customer_label:
                    parent = customer_label.find_parent()
                    if parent:
                        # Ищем следующий текст или элемент
                        next_text = parent.get_text(strip=True).replace('Заказчик', '').strip()
                        if next_text:
                            customer_text = next_text
                        else:
                            next_elem = parent.find_next_sibling()
                            if next_elem:
                                customer_text = next_elem.get_text(strip=True)

            if customer_text:
                # Часто в тексте заказчика есть ИНН: "ООО 'РОМАШКА' (ИНН 1234567890)"
                inn_match = re.search(r'ИНН\s*:?\s*(\d{10,12})', customer_text)
                if inn_match:
                    customer_inn = inn_match.group(1)
                    # Очищаем название от ИНН
                    customer_text = re.sub(r'\(?ИНН\s*:?\s*\d{10,12}\)?', '', customer_text).strip()
                
                item['customer_name'] = customer_text
                item['customerName'] = customer_text # Для совместимости
                if customer_inn:
                    item['customer_inn'] = customer_inn
                    item['customerInn'] = customer_inn
                    
                # Пытаемся извлечь регион из адреса заказчика
                region_match = re.search(r',\s*([А-Яа-яё\s]+(?:край|область|республика|АО|автономная\s+область))', customer_text)
                if region_match:
                    item['customerRegion'] = region_match.group(1).strip()
                    item['customer_region'] = item['customerRegion']
            
            # ВАЖНО: Извлекаем регион из номера закупки для 44-ФЗ
            # Первые 2 цифры номера извещения - код региона
            # Например: 0178... = СПб (78), 0150... = МО (50)
            if 'customer_region' not in item and item.get('id'):
                purchase_number = item['id']
                # Для 44-ФЗ номер имеет формат XXRR... где XX - тип, RR - код региона
                # Коды регионов: 01=Адыгея, 02=Башкортостан, ..., 77=Москва, 78=СПб
                if len(purchase_number) >= 4 and purchase_number[:2].isdigit():
                    # Извлекаем код региона (3-4 символы)
                    region_code = purchase_number[2:4]
                    # Маппинг кодов регионов в названия
                    region_code_map = {
                        "01": "Адыгея", "02": "Башкортостан", "03": "Бурятия", "04": "Алтай",
                        "05": "Дагестан", "06": "Ингушетия", "07": "Кабардино-Балкария",
                        "08": "Калмыкия", "09": "Карачаево-Черкесия", "10": "Карелия",
                        "11": "Коми", "12": "Марий Эл", "13": "Мордовия", "14": "Саха (Якутия)",
                        "15": "Северная Осетия", "16": "Татарстан", "17": "Тыва", "18": "Удмуртия",
                        "19": "Хакасия", "20": "Чечня", "21": "Чувашия", "22": "Алтайский край",
                        "23": "Краснодарский край", "24": "Красноярский край", "25": "Приморский край",
                        "26": "Ставропольский край", "27": "Хабаровский край", "28": "Амурская область",
                        "29": "Архангельская область", "30": "Астраханская область", "31": "Белгородская область",
                        "32": "Брянская область", "33": "Владимирская область", "34": "Волгоградская область",
                        "35": "Вологодская область", "36": "Воронежская область", "37": "Ивановская область",
                        "38": "Иркутская область", "39": "Калининградская область", "40": "Калужская область",
                        "41": "Камчатский край", "42": "Кемеровская область", "43": "Кировская область",
                        "44": "Костромская область", "45": "Курганская область", "46": "Курская область",
                        "47": "Ленинградская область", "48": "Липецкая область", "49": "Магаданская область",
                        "50": "Московская область", "51": "Мурманская область", "52": "Нижегородская область",
                        "53": "Новгородская область", "54": "Новосибирская область", "55": "Омская область",
                        "56": "Оренбургская область", "57": "Орловская область", "58": "Пензенская область",
                        "59": "Пермский край", "60": "Псковская область", "61": "Ростовская область",
                        "62": "Рязанская область", "63": "Самарская область", "64": "Саратовская область",
                        "65": "Сахалинская область", "66": "Свердловская область", "67": "Смоленская область",
                        "68": "Тамбовская область", "69": "Тверская область", "70": "Томская область",
                        "71": "Тульская область", "72": "Тюменская область", "73": "Ульяновская область",
                        "74": "Челябинская область", "75": "Забайкальский край", "76": "Ярославская область",
                        "77": "Москва", "78": "Санкт-Петербург", "79": "Еврейская АО",
                        "83": "Ненецкий АО", "86": "Ханты-Мансийский АО", "87": "Чукотский АО",
                        "89": "Ямало-Ненецкий АО", "91": "Крым", "92": "Севастополь"
                    }
                    if region_code in region_code_map:
                        item['customer_region'] = region_code_map[region_code]
                        item['customerRegion'] = region_code_map[region_code]
                        item['region_code'] = region_code
            
            # Электронная площадка
            platform_elem = card.find(string=re.compile(r'Размещение\s+осуществляет|Электронная\s+площадка', re.I))
            if platform_elem:
                parent = platform_elem.find_parent()
                if parent:
                    # Ищем текст площадки
                    platform_text = parent.get_text(strip=True)
                    # Очищаем от заголовка
                    platform_text = re.sub(r'Электронная\s+площадка\s*:?', '', platform_text, flags=re.I).strip()
                    if platform_text:
                        item['platform'] = platform_text
            
            # Дата публикации - улучшенный поиск
            date_text = None
            
            # Вариант 1: поиск по классу
            date_elem = (
                card.find('div', class_=re.compile(r'date|publish|published|data-block__title')) or
                card.find('span', class_=re.compile(r'date|publish|published')) or
                card.find('td', class_=re.compile(r'date|publish|published'))
            )
            
            if date_elem:
                date_text = date_elem.get_text(strip=True)
            
            # Вариант 2: поиск по тексту "опубликовано", "дата размещения"
            if not date_text or not re.search(r'\d', date_text):
                date_label = card.find(string=re.compile(r'опубликовано|дата\s+размещения|дата\s+публикации', re.I))
                if date_label:
                    parent = date_label.find_parent()
                    if parent:
                        date_text = parent.get_text(strip=True)
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            next_text = next_elem.get_text(strip=True)
                            if re.search(r'\d{2}\.\d{2}\.\d{4}', next_text):
                                date_text = next_text
            
            if date_text:
                # Извлекаем dd.mm.yyyy
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_text)
                if date_match:
                    item['publishDate'] = date_match.group(1)
                    item['publication_date'] = date_match.group(1)
            
            # Срок подачи заявок (Дедлайн)
            deadline_text = None
            deadline_label = card.find(string=re.compile(r'Окончание\s+подачи|Срок\s+подачи|До\s*:', re.I))
            if deadline_label:
                parent = deadline_label.find_parent()
                if parent:
                    # Ищем дату в том же элементе или соседе
                    search_text = parent.get_text(strip=True)
                    date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', search_text)
                    if not date_match:
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', next_elem.get_text(strip=True))
                    
                    if date_match:
                        deadline_text = date_match.group(1)
            
            if not deadline_text:
                # Ищем любую дату, которая не является датой публикации
                all_dates = re.findall(r'(\d{2}\.\d{2}\.\d{4})', card.get_text())
                if len(all_dates) >= 2:
                    # Обычно вторая дата - это дедлайн или дата проведения
                    deadline_text = all_dates[1]
                elif len(all_dates) == 1 and not item.get('publication_date'):
                    deadline_text = all_dates[0]
            
            if deadline_text:
                item['applicationDeadline'] = deadline_text
                item['application_deadline'] = deadline_text
            
            if item.get('id') or item.get('eis_id') or item.get('title'):
                return item
            
            return None
        except Exception as e:
            logger.debug(f"Error in _parse_tender_card: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
