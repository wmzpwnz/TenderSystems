"""
Клиент для работы с SOAP API ЕИС zakupki.gov.ru

Использует официальные сервисы отдачи данных в машиночитаемом виде:
- getDocsIP — для физических лиц: https://int.zakupki.gov.ru/eis-integration/services/getDocsIP
- getDocsLE — для юридических лиц: https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE

Для работы с указанными сервисами необходимо пройти регистрацию и авторизацию 
с использованием единой системы идентификации и аутентификации (ЕСИА).

Токен получается через личный кабинет получателя открытых данных:
https://zakupki.gov.ru/epz/opendata/search/results.html

Источник: Ответ службы технической поддержки ГИС ЕИС ЗАКУПКИ от 05.01.2026
"""
import uuid
import datetime
import httpx  # Заменили requests на httpx для async
import xmltodict
from typing import Dict, List, Optional, Literal
import logging
import os
import zipfile
import io
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class EISSOAPClient:
    """
    Клиент для работы с SOAP API ЕИС
    
    Поддерживает два типа сервисов:
    - getDocsIP: для физических лиц (ФЛ)
    - getDocsLE: для юридических лиц (ЮЛ)
    """
    
    # Новые URL сервисов согласно ответу службы поддержки от 05.01.2026
    SERVICE_URLS = {
        'IP': 'https://int.zakupki.gov.ru/eis-integration/services/getDocsIP',  # Физические лица
        'LE': 'https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE'  # Юридические лица
    }

    SERVICE_NAMESPACES = {
        'IP': 'http://zakupki.gov.ru/fz44/get-docs-ip/ws',
        'LE': 'http://zakupki.gov.ru/fz44/get-docs-le/ws',
    }
    
    def __init__(
        self, 
        token: Optional[str] = None,
        user_type: Literal['IP', 'LE'] = 'IP'
    ):
        """
        Инициализация SOAP клиента
        
        Args:
            token: Токен авторизации (получается через ЕСИА в личном кабинете)
            user_type: Тип пользователя ('IP' - физическое лицо, 'LE' - юридическое лицо)
        """
        self.user_type = user_type
        self.token = token or os.getenv("EIS_SOAP_TOKEN", "")
        
        # Определяем URL сервиса в зависимости от типа пользователя
        self.base_url = self.SERVICE_URLS.get(user_type, self.SERVICE_URLS['IP'])
        
        # Для юридических лиц может потребоваться отдельный токен
        if user_type == 'LE':
            le_token = os.getenv("EIS_SOAP_TOKEN_LE", "")
            if le_token:
                self.token = le_token
        
        if not self.token:
            logger.warning(
                f"EIS SOAP token not provided for {user_type}. "
                f"Set EIS_SOAP_TOKEN (для ФЛ) or EIS_SOAP_TOKEN_LE (для ЮЛ) in .env. "
                f"Токен можно получить в личном кабинете: "
                f"https://zakupki.gov.ru/epz/opendata/search/results.html"
            )

    def _redact_sensitive(self, value):
        """Redact SOAP token from values before logging."""
        if isinstance(value, dict):
            return {key: self._redact_sensitive(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._redact_sensitive(item) for item in value]
        if isinstance(value, str) and self.token:
            return value.replace(self.token, "[REDACTED]")
        return value
    
    def _build_soap_envelope(
        self,
        method: str,
        selection_params: Dict
    ) -> str:
        """
        Формирует SOAP envelope для запроса
        
        Args:
            method: Название метода (getDocsByReestrNumberRequest, getDocsByOrgRegionRequest и т.д.)
            selection_params: Параметры запроса
        """
        generated_uuid = str(uuid.uuid4())
        generated_datetime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        
        # Базовый SOAP envelope
        # ВАЖНО: Токен должен быть и в SOAP Header, и в HTTP заголовке!
        # Для ФЛ используется individualPerson_token, для ЮЛ - legalEntity_token
        if self.token:
            if self.user_type == 'LE':
                header_token = f"""    <soapenv:Header>
        <legalEntity_token>{self.token}</legalEntity_token>
    </soapenv:Header>"""
            else:
                header_token = f"""    <soapenv:Header>
        <individualPerson_token>{self.token}</individualPerson_token>
    </soapenv:Header>"""
        else:
            header_token = "    <soapenv:Header/>"
        
        # Определяем namespace в зависимости от типа пользователя
        namespace_url = self.SERVICE_NAMESPACES.get(self.user_type, self.SERVICE_NAMESPACES['IP'])
        
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="{namespace_url}">
{header_token}
    <soapenv:Body>
        <ws:{method}>
            <index>
                <id>{generated_uuid}</id>
                <createDateTime>{generated_datetime}</createDateTime>
                <mode>PROD</mode>
            </index>
            <selectionParams>
                {self._build_selection_params(selection_params)}
            </selectionParams>
        </ws:{method}>
    </soapenv:Body>
</soapenv:Envelope>"""
        
        return envelope
    
    def _build_selection_params(self, params: Dict) -> str:
        """Формирует блок selectionParams
        
        ВАЖНО: Порядок тегов имеет значение в SOAP!
        Правильный порядок согласно схеме:
        1. subsystemType
        2. orgRegion (для getDocsByOrgRegionRequest)
        3. documentType44 (для getDocsByOrgRegionRequest)
        4. periodInfo
        5. reestrNumber (для getDocsByReestrNumberRequest)
        """
        xml_parts = []
        
        # Порядок тегов ВАЖЕН в SOAP! Согласно рабочему примеру:
        # Для getDocsByOrgRegionRequest: orgRegion, subsystemType, documentType44, periodInfo
        # Для getDocsByReestrNumberRequest: subsystemType, reestrNumber
        
        if 'orgRegion' in params:
            # Для getDocsByOrgRegionRequest - orgRegion первый
            xml_parts.append(f"<orgRegion>{params['orgRegion']}</orgRegion>")
        
        if 'subsystemType' in params:
            xml_parts.append(f"<subsystemType>{params['subsystemType']}</subsystemType>")
        
        if 'documentType44' in params:
            xml_parts.append(f"<documentType44>{params['documentType44']}</documentType44>")
        
        if 'periodInfo' in params:
            period = params['periodInfo']
            xml_parts.append("<periodInfo>")
            if 'exactDate' in period:
                xml_parts.append(f"<exactDate>{period['exactDate']}</exactDate>")
            elif 'startDate' in period and 'endDate' in period:
                xml_parts.append(f"<startDate>{period['startDate']}</startDate>")
                xml_parts.append(f"<endDate>{period['endDate']}</endDate>")
            xml_parts.append("</periodInfo>")
        
        if 'reestrNumber' in params:
            # Для getDocsByReestrNumberRequest
            xml_parts.append(f"<reestrNumber>{params['reestrNumber']}</reestrNumber>")
        
        return "\n                ".join(xml_parts)
    
    async def _make_soap_request(self, xml_data: str) -> Optional[Dict]:
        """Выполняет SOAP запрос (async через httpx)"""
        try:
            # Определяем заголовок токена в зависимости от типа пользователя
            token_header_name = 'legalEntity_token' if self.user_type == 'LE' else 'individualPerson_token'
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                token_header_name: self.token
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    content=xml_data.encode('utf-8'),
                    headers=headers,
                    timeout=30.0
                )

            if response.status_code == 200:
                try:
                    return xmltodict.parse(response.content)
                except Exception as e:
                    logger.error(f"Error parsing SOAP response: {e}")
                    return None
            else:
                logger.error(f"SOAP request failed: {response.status_code} - {response.text[:500]}")
                return None

        except Exception as e:
            logger.error(f"Error making SOAP request: {e}")
            return None
    
    async def _download_archive(self, archive_url: str) -> Optional[bytes]:
        """Скачивает архив по URL (требует токен в headers!)"""
        try:
            # Определяем заголовок токена в зависимости от типа пользователя
            token_header_name = 'legalEntity_token' if self.user_type == 'LE' else 'individualPerson_token'
            
            headers = {
                token_header_name: self.token,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
            }

            # Пробуем скачать архив (async через httpx)
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    archive_url,
                    headers=headers,
                    timeout=120.0
                )

            if response.status_code == 200:
                logger.debug(f"Successfully downloaded archive, size: {len(response.content)} bytes")
                return response.content
            elif response.status_code == 404:
                logger.warning(f"Archive not found (404): {archive_url[:100]}...")
                return None
            else:
                logger.error(f"Error downloading archive: {response.status_code}, URL: {archive_url[:100]}...")
                logger.debug(f"Response headers: {dict(response.headers)}")
                return None

        except httpx.TimeoutException:
            logger.error(f"Timeout downloading archive: {archive_url[:100]}...")
            return None
        except Exception as e:
            logger.error(f"Error downloading archive: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    async def get_docs_by_reestr_number(
        self,
        reestr_number: str,
        subsystem_type: str = "PRIZ"
    ) -> Optional[str]:
        """
        Получить документы по реестровому номеру закупки
        
        Args:
            reestr_number: Реестровый номер закупки (например, "0888200000224000038")
            subsystem_type: Тип подсистемы (PRIZ - извещения)
        
        Returns:
            URL архива с документами или None
        """
        selection_params = {
            'subsystemType': subsystem_type,
            'reestrNumber': reestr_number
        }
        
        xml_data = self._build_soap_envelope('getDocsByReestrNumberRequest', selection_params)
        response = await self._make_soap_request(xml_data)
        
        if response:
            try:
                # Пробуем разные варианты структуры ответа (xmltodict может использовать разные namespace)
                envelope = response.get('soap:Envelope') or response.get('soapenv:Envelope') or response.get('Envelope') or {}
                body = envelope.get('soap:Body') or envelope.get('soapenv:Body') or envelope.get('Body') or {}
                
                # Если body - это не dict, значит структура другая
                if not isinstance(body, dict):
                    logger.error(f"Unexpected body structure: {type(body)}")
                    return None
                
                # Ищем ответ в разных форматах
                response_key = None
                for key in body.keys():
                    if 'getDocsByReestrNumberResponse' in key or 'Response' in key:
                        response_key = key
                        break
                
                if response_key:
                    response_data = body[response_key]
                    
                    # Отладочная информация
                    logger.debug(f"response_data type: {type(response_data)}")
                    logger.debug(f"response_data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'not dict'}")
                    
                    data_info = response_data.get('dataInfo', {})
                    logger.debug(f"data_info type: {type(data_info)}")
                    logger.debug(f"data_info: {self._redact_sensitive(data_info)}")
                    
                    # Проверяем наличие ошибки
                    if isinstance(data_info, dict) and 'errorInfo' in data_info:
                        error_info = data_info.get('errorInfo', {})
                        if isinstance(error_info, dict):
                            error_msg = error_info.get('errorMessage') or error_info.get('message') or str(error_info)
                            error_code = error_info.get('errorCode') or error_info.get('code', '')
                            logger.error(f"SOAP API returned error: {self._redact_sensitive(error_msg)} (code: {error_code})")
                        else:
                            logger.error(f"SOAP API returned error: {self._redact_sensitive(error_info)}")
                        logger.debug(f"Full errorInfo: {self._redact_sensitive(error_info)}")
                        return None
                    
                    # archiveUrl может быть массивом или строкой
                    archive_url = data_info.get('archiveUrl') if isinstance(data_info, dict) else None
                    
                    if archive_url:
                        # Если это массив, берем первый элемент
                        if isinstance(archive_url, list) and len(archive_url) > 0:
                            logger.info(f"Found {len(archive_url)} archive URLs, using first one")
                            return archive_url[0]
                        elif isinstance(archive_url, str):
                            return archive_url
                    else:
                        logger.warning(f"archiveUrl not found. data_info keys: {list(data_info.keys()) if isinstance(data_info, dict) else 'N/A'}")
                
                # Если не нашли, логируем структуру для отладки
                logger.debug(f"Response structure: {self._redact_sensitive(response)}")
                logger.error(f"Could not find archiveUrl in response. Keys: {list(body.keys())}")
                return None
            except Exception as e:
                logger.error(f"Error extracting archive URL: {e}")
                logger.debug(f"Response structure: {self._redact_sensitive(response)}")
                return None
        
        return None
    
    async def get_docs_by_org_region(
        self,
        org_region: str,
        document_type: str = "epNotificationEF2020",
        date: Optional[str] = None,
        subsystem_type: str = "PRIZ"
    ) -> Optional[str]:
        """
        Получить документы по региону заказчика
        
        Args:
            org_region: Код региона (например, "72" для Тюменской области, "77" для Москвы)
            document_type: Тип документа (epNotificationEF2020 - извещения)
            date: Дата в формате YYYY-MM-DD (если None - текущая дата)
            subsystem_type: Тип подсистемы (PRIZ - извещения)
        
        Returns:
            URL архива с документами или None
        """
        if date is None:
            date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        selection_params = {
            'orgRegion': org_region,
            'subsystemType': subsystem_type,
            'documentType44': document_type,
            'periodInfo': {
                'exactDate': date
            }
        }
        
        xml_data = self._build_soap_envelope('getDocsByOrgRegionRequest', selection_params)
        response = await self._make_soap_request(xml_data)
        
        if response:
            try:
                # Пробуем разные варианты структуры ответа (xmltodict может использовать разные namespace)
                envelope = response.get('soap:Envelope') or response.get('soapenv:Envelope') or response.get('Envelope') or {}
                body = envelope.get('soap:Body') or envelope.get('soapenv:Body') or envelope.get('Body') or {}
                
                # Если body - это не dict, значит структура другая
                if not isinstance(body, dict):
                    logger.error(f"Unexpected body structure: {type(body)}")
                    return None
                
                # Ищем ответ в разных форматах
                response_key = None
                for key in body.keys():
                    if 'getDocsByOrgRegionResponse' in key or 'Response' in key:
                        response_key = key
                        break
                
                if response_key:
                    response_data = body[response_key]
                    
                    # Отладочная информация
                    logger.debug(f"response_data type: {type(response_data)}")
                    logger.debug(f"response_data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'not dict'}")
                    
                    data_info = response_data.get('dataInfo', {})
                    logger.debug(f"data_info type: {type(data_info)}")
                    logger.debug(f"data_info: {self._redact_sensitive(data_info)}")
                    
                    # Проверяем наличие ошибки
                    if isinstance(data_info, dict) and 'errorInfo' in data_info:
                        error_info = data_info.get('errorInfo', {})
                        if isinstance(error_info, dict):
                            error_msg = error_info.get('errorMessage') or error_info.get('message') or str(error_info)
                            error_code = error_info.get('errorCode') or error_info.get('code', '')
                            logger.error(f"SOAP API returned error: {self._redact_sensitive(error_msg)} (code: {error_code})")
                        else:
                            logger.error(f"SOAP API returned error: {self._redact_sensitive(error_info)}")
                        logger.debug(f"Full errorInfo: {self._redact_sensitive(error_info)}")
                        return None
                    
                    # archiveUrl может быть массивом или строкой
                    archive_url = data_info.get('archiveUrl') if isinstance(data_info, dict) else None
                    
                    if archive_url:
                        # Если это массив, берем первый элемент
                        if isinstance(archive_url, list) and len(archive_url) > 0:
                            logger.info(f"Found {len(archive_url)} archive URLs, using first one")
                            return archive_url[0]
                        elif isinstance(archive_url, str):
                            return archive_url
                    else:
                        logger.warning(f"archiveUrl not found. data_info keys: {list(data_info.keys()) if isinstance(data_info, dict) else 'N/A'}")
                
                # Если не нашли, логируем структуру для отладки
                logger.debug(f"Response structure: {self._redact_sensitive(response)}")
                logger.error(f"Could not find archiveUrl in response. Keys: {list(body.keys())}")
                return None
            except Exception as e:
                logger.error(f"Error extracting archive URL: {e}")
                logger.debug(f"Response structure: {self._redact_sensitive(response)}")
                return None
        
        return None
    
    async def download_and_parse_archive(self, archive_url: str) -> List[Dict]:
        """
        Скачивает архив и парсит XML документы из него

        Returns:
            Список словарей с данными о закупках
        """
        archive_data = await self._download_archive(archive_url)
        
        if not archive_data:
            return []
        
        tenders = []
        
        try:
            # Распаковываем ZIP архив
            with zipfile.ZipFile(io.BytesIO(archive_data), 'r') as zip_ref:
                xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
                
                for xml_file in xml_files:
                    try:
                        xml_content = zip_ref.read(xml_file)
                        # Парсим XML файл - может содержать один или несколько тендеров
                        tender_data_list = self._parse_export_xml(xml_content)
                        if tender_data_list:
                            tenders.extend(tender_data_list)
                    except Exception as e:
                        logger.debug(f"Error parsing {xml_file}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error extracting archive: {e}")
            return []
        
        return tenders
    
    def _parse_export_xml(self, xml_content: bytes) -> List[Dict]:
        """Парсит XML файл экспорта (может содержать несколько тендеров)"""
        try:
            root = ET.fromstring(xml_content)
            
            # Определяем namespace
            ep_ns = 'http://zakupki.gov.ru/oos/EPtypes/1'
            
            logger.debug(f"Parsing XML, root tag: {root.tag}")
            
            # Проверяем, это экспортный формат или отдельное извещение
            if root.tag.endswith('}export') or 'export' in root.tag.lower():
                # Экспортный формат - ищем все извещения внутри
                tenders = []
                found_notifications = []
                
                # Сначала пробуем найти напрямую дочерние элементы
                for child in root:
                    tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if 'Notification' in tag_name or 'notification' in tag_name.lower():
                        found_notifications.append(child)
                        logger.debug(f"Found notification child: {child.tag}")
                
                # Если не нашли, ищем рекурсивно
                if not found_notifications:
                    # Ищем элементы извещений напрямую по namespace и тегу
                    notification_tags = [
                        f'.//{{{ep_ns}}}epNotificationEF2020',
                        f'.//{{{ep_ns}}}epNotificationEF',
                        f'.//{{{ep_ns}}}epNotification',
                        './/{http://zakupki.gov.ru/oos/EPtypes/1}epNotificationEF2020',
                        './/{http://zakupki.gov.ru/oos/EPtypes/1}epNotificationEF',
                        './/{http://zakupki.gov.ru/oos/EPtypes/1}epNotification',
                    ]
                    
                    for tag_pattern in notification_tags:
                        found = root.findall(tag_pattern)
                        if found:
                            found_notifications.extend(found)
                            logger.debug(f"Found {len(found)} notifications with pattern {tag_pattern}")
                            break
                
                # Если все еще не нашли, ищем по содержимому тега
                if not found_notifications:
                    for elem in root.iter():
                        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if tag_name in ['epNotificationEF2020', 'epNotificationEF', 'epNotification']:
                            # Проверяем, что это не вложенный элемент (нет родителя с Notification)
                            parent = elem.getparent() if hasattr(elem, 'getparent') else None
                            if parent is None or parent == root:
                                found_notifications.append(elem)
                                logger.debug(f"Found notification by iter: {elem.tag}")
                
                logger.info(f"Found {len(found_notifications)} notification elements to parse")
                
                if not found_notifications:
                    # Логируем структуру для отладки
                    logger.warning("No notifications found! XML structure:")
                    logger.warning(f"Root tag: {root.tag}")
                    for i, child in enumerate(list(root)[:3]):
                        logger.warning(f"  Child {i}: {child.tag}")
                        # Проверяем, есть ли внутри что-то полезное
                        for subchild in list(child)[:2]:
                            logger.warning(f"    Subchild: {subchild.tag}")
                
                # Парсим найденные извещения
                for notification in found_notifications:
                    tender_data = self._parse_notification_element(notification)
                    if tender_data:
                        tenders.append(tender_data)
                        logger.info(f"Parsed tender: {tender_data.get('id', 'N/A')}, title: {tender_data.get('title', 'N/A')[:50]}")
                        logger.info(f"  customer_name: {tender_data.get('customerName')}, price: {tender_data.get('initialPrice')}, region: {tender_data.get('customerRegion')}")
                    else:
                        logger.warning(f"Failed to parse notification element: {notification.tag}")
                        # Логируем структуру элемента для отладки
                        common_info = notification.find(f'.//{{{ep_ns}}}commonInfo')
                        logger.warning(f"  commonInfo found: {common_info is not None}")
                        if common_info is not None:
                            purchase_number = common_info.find(f'{{{ep_ns}}}purchaseNumber')
                            logger.warning(f"  purchaseNumber found: {purchase_number is not None}")
                
                logger.info(f"Parsed {len(tenders)} tenders from XML export")
                return tenders
            else:
                # Отдельное извещение
                logger.debug("Parsing as single notification")
                tender_data = self._parse_notification_element(root)
                return [tender_data] if tender_data else []
        except Exception as e:
            logger.error(f"Error parsing export XML: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _parse_notification_element(self, notification_elem) -> Optional[Dict]:
        """Парсит элемент извещения о закупке"""
        try:
            import re
            
            # Определяем namespace (поддержка разных версий схем)
            namespaces = {
                'ns': 'http://zakupki.gov.ru/oos/types/1',
                'ns223': 'http://zakupki.gov.ru/223fz/types/1',
                'ns44': 'http://zakupki.gov.ru/223fz/types/1',  # 44-ФЗ
                'ns5': 'http://zakupki.gov.ru/oos/EPtypes/1',  # EPtypes для извещений
                'ns4': 'http://zakupki.gov.ru/oos/common/1',  # Common
                'ns2': 'http://zakupki.gov.ru/oos/base/1',  # Base
            }
            
            tender = {}
            
            # Определяем namespace из элемента
            ep_ns = 'http://zakupki.gov.ru/oos/EPtypes/1'
            base_ns = 'http://zakupki.gov.ru/oos/base/1'
            common_ns = 'http://zakupki.gov.ru/oos/common/1'
            
            # Ищем commonInfo для получения номера закупки
            common_info = notification_elem.find(f'.//{{{ep_ns}}}commonInfo')
            if common_info is not None:
                purchase_number = common_info.find(f'{{{ep_ns}}}purchaseNumber')
                if purchase_number is not None and purchase_number.text:
                    tender['id'] = purchase_number.text
                    tender['number'] = purchase_number.text
                    tender['eis_id'] = purchase_number.text
                
                # Название закупки
                purchase_object_info = common_info.find(f'{{{ep_ns}}}purchaseObjectInfo')
                if purchase_object_info is not None and purchase_object_info.text:
                    tender['title'] = purchase_object_info.text
                    tender['purchaseObjectInfo'] = purchase_object_info.text
                
                # Дата публикации
                publish_dt = common_info.find(f'{{{ep_ns}}}publishDTInEIS')
                if publish_dt is not None and publish_dt.text:
                    tender['publishDate'] = publish_dt.text
                
                # Ссылка на документы
                href = common_info.find(f'{{{ep_ns}}}href')
                if href is not None and href.text:
                    tender['documentsUrl'] = href.text
            
            # Заказчик из purchaseResponsibleInfo
            responsible_info = notification_elem.find(f'.//{{{ep_ns}}}purchaseResponsibleInfo')
            if responsible_info is not None:
                responsible_org = responsible_info.find(f'.//{{{ep_ns}}}responsibleOrgInfo')
                if responsible_org is not None:
                    full_name = responsible_org.find(f'{{{ep_ns}}}fullName')
                    if full_name is not None and full_name.text:
                        tender['customerName'] = full_name.text
                    
                    # ИНН заказчика
                    inn = responsible_org.find(f'{{{ep_ns}}}INN')
                    if inn is not None and inn.text:
                        tender['customerInn'] = inn.text
                    
                    # КПП заказчика
                    kpp = responsible_org.find(f'{{{ep_ns}}}KPP')
                    if kpp is not None and kpp.text:
                        tender['customerKpp'] = kpp.text
                    
                    # Извлекаем регион из адреса
                    post_address = responsible_org.find(f'{{{ep_ns}}}postAddress')
                    fact_address = responsible_org.find(f'{{{ep_ns}}}factAddress')
                    address = None
                    if post_address is not None and post_address.text:
                        address = post_address.text
                    elif fact_address is not None and fact_address.text:
                        address = fact_address.text
                    
                    if address:
                        # Пытаемся извлечь регион из адреса
                        # Формат: "Российская Федерация, индекс, Регион, ..."
                        region_match = re.search(r',\s*([А-Яа-яё\s]+(?:край|область|республика|АО|автономная\s+область))', address)
                        if region_match:
                            tender['customerRegion'] = region_match.group(1).strip()
                        else:
                            # Альтернативный вариант - ищем по известным регионам
                            regions = [
                                'Москва', 'Санкт-Петербург', 'Московская область', 'Ленинградская область',
                                'Тюменская область', 'Свердловская область', 'Краснодарский край',
                                'Пермский край', 'Республика Татарстан', 'Республика Башкортостан'
                            ]
                            for region in regions:
                                if region in address:
                                    tender['customerRegion'] = region
                                    break
            
            # Цена и условия контракта из notificationInfo -> contractConditionsInfo -> maxPriceInfo
            notification_info = notification_elem.find(f'.//{{{ep_ns}}}notificationInfo')
            if notification_info is not None:
                contract_conditions = notification_info.find(f'.//{{{ep_ns}}}contractConditionsInfo')
                if contract_conditions is not None:
                    max_price_info = contract_conditions.find(f'.//{{{ep_ns}}}maxPriceInfo')
                    if max_price_info is not None:
                        max_price = max_price_info.find(f'{{{ep_ns}}}maxPrice')
                        if max_price is not None and max_price.text:
                            try:
                                price_text = max_price.text.replace(' ', '').replace(',', '.').strip()
                                if price_text:
                                    tender['price'] = float(price_text)
                                    tender['initialPrice'] = tender['price']
                            except (ValueError, AttributeError):
                                pass
                        
                        # Валюта
                        currency = max_price_info.find(f'.//{{{base_ns}}}code')
                        if currency is not None and currency.text:
                            tender['currency'] = currency.text
                    
                    # Срок исполнения контракта из contractExecutionTermsInfo
                    execution_terms = contract_conditions.find(f'.//{{{ep_ns}}}contractExecutionTermsInfo')
                    if execution_terms is None:
                        # Пробуем найти в customerRequirementsInfo
                        customer_req = notification_info.find(f'.//{{{ep_ns}}}customerRequirementsInfo')
                        if customer_req is not None:
                            customer_req_info = customer_req.find(f'.//{{{ep_ns}}}customerRequirementInfo')
                            if customer_req_info is not None:
                                contract_cond = customer_req_info.find(f'.//{{{ep_ns}}}contractConditionsInfo')
                                if contract_cond is not None:
                                    execution_terms = contract_cond.find(f'.//{{{ep_ns}}}contractExecutionTermsInfo')
                    
                    if execution_terms is not None:
                        # Ищем относительные сроки
                        relative_terms = execution_terms.find(f'.//{{{common_ns}}}relativeTermsInfo')
                        if relative_terms is not None:
                            term = relative_terms.find(f'.//{{{common_ns}}}term')
                            if term is not None and term.text:
                                try:
                                    tender['contractDeadlineDays'] = int(term.text)
                                except (ValueError, AttributeError):
                                    pass
                
                # Срок подачи заявок из procedureInfo -> collectingInfo
                procedure_info = notification_info.find(f'.//{{{ep_ns}}}procedureInfo')
                if procedure_info is not None:
                    collecting_info = procedure_info.find(f'.//{{{ep_ns}}}collectingInfo')
                    if collecting_info is not None:
                        end_dt = collecting_info.find(f'{{{ep_ns}}}endDT')
                        if end_dt is not None and end_dt.text:
                            tender['applicationDeadline'] = end_dt.text
                        
                        start_dt = collecting_info.find(f'{{{ep_ns}}}startDT')
                        if start_dt is not None and start_dt.text:
                            tender['applicationStartDate'] = start_dt.text
                    
                    # Дата проведения торгов
                    bidding_date = procedure_info.find(f'{{{ep_ns}}}biddingDate')
                    if bidding_date is not None and bidding_date.text:
                        tender['biddingDate'] = bidding_date.text
                    
                    # Дата подведения итогов
                    summarizing_date = procedure_info.find(f'{{{ep_ns}}}summarizingDate')
                    if summarizing_date is not None and summarizing_date.text:
                        tender['summarizingDate'] = summarizing_date.text
                
                # Тип процедуры из commonInfo -> placingWay
                if common_info is not None:
                    placing_way = common_info.find(f'.//{{{ep_ns}}}placingWay')
                    if placing_way is not None:
                        procedure_code = placing_way.find(f'.//{{{base_ns}}}code')
                        if procedure_code is not None and procedure_code.text:
                            tender['procedureCode'] = procedure_code.text
                        
                        procedure_name = placing_way.find(f'.//{{{base_ns}}}name')
                        if procedure_name is not None and procedure_name.text:
                            tender['procedureType'] = procedure_name.text
                
                # ОКПД2 коды из purchaseObjectsInfo
                purchase_objects = notification_info.find(f'.//{{{ep_ns}}}purchaseObjectsInfo')
                if purchase_objects is not None:
                    okpd2_codes = []
                    for okpd2_elem in purchase_objects.findall(f'.//{{{common_ns}}}OKPD2'):
                        okpd_code = okpd2_elem.find(f'.//{{{base_ns}}}OKPDCode')
                        if okpd_code is not None and okpd_code.text:
                            okpd2_codes.append(okpd_code.text)
                    if okpd2_codes:
                        tender['okpd2Codes'] = okpd2_codes
                
                # Требования к участникам из requirementsInfo
                requirements_info = notification_info.find(f'.//{{{ep_ns}}}requirementsInfo')
                if requirements_info is not None:
                    requirements = []
                    for req_info in requirements_info.findall(f'.//{{{ep_ns}}}requirementInfo'):
                        pref_req = req_info.find(f'.//{{{common_ns}}}preferenseRequirementInfo')
                        if pref_req is not None:
                            req_name = pref_req.find(f'.//{{{base_ns}}}name')
                            if req_name is not None and req_name.text:
                                requirements.append(req_name.text)
                    if requirements:
                        tender['requirements'] = requirements
            
            # Документы из attachmentsInfo
            attachments_info = notification_elem.find(f'.//{{{ep_ns}}}attachmentsInfo')
            if attachments_info is not None:
                documents = []
                for attachment in attachments_info.findall(f'.//{{{common_ns}}}attachmentInfo'):
                    doc = {}
                    file_name = attachment.find(f'{{{common_ns}}}fileName')
                    if file_name is not None and file_name.text:
                        doc['fileName'] = file_name.text
                    
                    doc_url = attachment.find(f'{{{common_ns}}}url')
                    if doc_url is not None and doc_url.text:
                        doc['url'] = doc_url.text
                    
                    doc_desc = attachment.find(f'{{{common_ns}}}docDescription')
                    if doc_desc is not None and doc_desc.text:
                        doc['description'] = doc_desc.text
                    
                    doc_date = attachment.find(f'{{{common_ns}}}docDate')
                    if doc_date is not None and doc_date.text:
                        doc['date'] = doc_date.text
                    
                    doc_kind = attachment.find(f'.//{{{base_ns}}}name')
                    if doc_kind is not None and doc_kind.text:
                        doc['kind'] = doc_kind.text
                    
                    if doc:
                        documents.append(doc)
                
                if documents:
                    tender['documents'] = documents
                    tender['documents_data'] = documents
            
            # Обеспечение заявки и контракта из guaranteeInfo
            if notification_info is not None:
                # Обеспечение заявки
                application_guarantee = notification_info.find(f'.//{{{ep_ns}}}applicationGuaranteeInfo')
                if application_guarantee is not None:
                    guarantee_amount = application_guarantee.find(f'{{{ep_ns}}}applicationGuaranteeAmount')
                    if guarantee_amount is not None and guarantee_amount.text:
                        try:
                            amount_text = guarantee_amount.text.replace(' ', '').replace(',', '.').strip()
                            if amount_text:
                                tender['guaranteeAmount'] = float(amount_text)
                                tender['guarantee_amount'] = float(amount_text)
                        except (ValueError, AttributeError):
                            pass

                # Обеспечение контракта
                contract_guarantee_info = notification_info.find(f'.//{{{ep_ns}}}contractGuaranteeInfo')
                if contract_guarantee_info is not None:
                    contract_guarantee_amount = contract_guarantee_info.find(f'{{{ep_ns}}}contractGuaranteeAmount')
                    if contract_guarantee_amount is not None and contract_guarantee_amount.text:
                        try:
                            amount_text = contract_guarantee_amount.text.replace(' ', '').replace(',', '.').strip()
                            if amount_text:
                                tender['contractGuarantee'] = float(amount_text)
                                tender['contract_guarantee'] = float(amount_text)
                        except (ValueError, AttributeError):
                            pass

                # Авансирование из contractConditionsInfo
                if contract_conditions is not None:
                    prepayment_info = contract_conditions.find(f'.//{{{ep_ns}}}prepaymentInfo')
                    if prepayment_info is not None:
                        prepayment_exists = prepayment_info.find(f'{{{ep_ns}}}prepaymentExists')
                        if prepayment_exists is not None and prepayment_exists.text:
                            has_prepayment = prepayment_exists.text.lower() == 'true'

                            # Определяем тип по процедуре
                            procedure_type_text = tender.get('procedureType', '')
                            is_44fz = '44' in procedure_type_text or 'Электронный аукцион' in procedure_type_text or \
                                     'Конкурс' in procedure_type_text or 'Запрос' in procedure_type_text
                            is_223fz = '223' in procedure_type_text

                            if has_prepayment:
                                if is_44fz:
                                    tender['prepayment_type'] = 'prepayment_44fz'
                                elif is_223fz:
                                    tender['prepayment_type'] = 'prepayment_223fz'
                                else:
                                    tender['prepayment_type'] = 'prepayment_44fz'
                            else:
                                tender['prepayment_type'] = 'no_prepayment'

                # Преимущества и ограничения из customerRequirementsInfo
                customer_requirements = notification_info.find(f'.//{{{ep_ns}}}customerRequirementsInfo')
                if customer_requirements is not None:
                    preferences = []

                    # СМП/СОНКО
                    smp_info = customer_requirements.find(f'.//{{{ep_ns}}}smallBusinessParticipationInfo')
                    if smp_info is not None:
                        smp_required = smp_info.find(f'{{{ep_ns}}}smallBusinessParticipationRequired')
                        if smp_required is not None and smp_required.text and smp_required.text.lower() == 'true':
                            preferences.append('smp_sonko')

                    # УИС
                    uis_info = customer_requirements.find(f'.//{{{ep_ns}}}penitentiaryInfo')
                    if uis_info is not None:
                        uis_required = uis_info.find(f'{{{ep_ns}}}penitentiaryRequired')
                        if uis_required is not None and uis_required.text and uis_required.text.lower() == 'true':
                            preferences.append('uis')

                    # Организации инвалидов
                    disabled_info = customer_requirements.find(f'.//{{{ep_ns}}}disabledOrganizationsInfo')
                    if disabled_info is not None:
                        disabled_required = disabled_info.find(f'{{{ep_ns}}}disabledOrganizationsRequired')
                        if disabled_required is not None and disabled_required.text and disabled_required.text.lower() == 'true':
                            preferences.append('disabled_orgs')

                    # Национальный режим
                    national_info = customer_requirements.find(f'.//{{{ep_ns}}}nationalRegimeInfo')
                    if national_info is not None:
                        national_required = national_info.find(f'{{{ep_ns}}}nationalRegimeRequired')
                        if national_required is not None and national_required.text and national_required.text.lower() == 'true':
                            preferences.append('national_regime')

                    if preferences:
                        tender['preferences'] = preferences

                # Площадка из procedureInfo -> electronicAuctionInfo -> electronicPlaceInfo
                if procedure_info is not None:
                    electronic_auction = procedure_info.find(f'.//{{{ep_ns}}}electronicAuctionInfo')
                    if electronic_auction is not None:
                        electronic_place = electronic_auction.find(f'.//{{{ep_ns}}}electronicPlaceInfo')
                        if electronic_place is not None:
                            place_name = electronic_place.find(f'{{{ep_ns}}}electronicPlaceName')
                            if place_name is not None and place_name.text:
                                platform_text = place_name.text
                                # Нормализуем название площадки
                                platform_mapping = {
                                    'РТС-тендер': 'roseltorg',
                                    'Сбербанк-АСТ': 'sberbank-ast',
                                    'ЭТП ГПБ': 'etp-gpb',
                                    'ЕЭТП': 'eetp',
                                    'Фабрикант': 'fabricant',
                                    'Lot-online': 'lot-online',
                                    'Заказ.РФ': 'zakazrf',
                                }

                                for key, value in platform_mapping.items():
                                    if key in platform_text:
                                        tender['platform'] = value
                                        break

            # Статус по умолчанию
            tender['status'] = 'active'

            # Логируем результат парсинга
            logger.debug(f"Parsed tender data: id={tender.get('id')}, title={tender.get('title')}, customerName={tender.get('customerName')}, initialPrice={tender.get('initialPrice')}")

            return tender if tender.get('id') or tender.get('title') else None
        
        except Exception as e:
            logger.debug(f"Error parsing notification element: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    async def search_tenders(
        self,
        region: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Поиск тендеров через SOAP API
        
        Args:
            region: Код региона (например, "77" для Москвы)
            date: Дата в формате YYYY-MM-DD
            limit: Максимальное количество (ограничение на количество архивов)
        
        Returns:
            Список тендеров
        """
        if not self.token:
            logger.error("Token is required for SOAP API")
            return []
        
        # Если регион не указан, используем популярные регионы
        if not region:
            regions = ["77", "78", "50", "72"]  # Москва, СПб, МО, Тюмень
        else:
            regions = [region]
        
        all_tenders = []
        
        for reg in regions[:limit]:
            try:
                archive_url = await self.get_docs_by_org_region(
                    org_region=reg,
                    date=date
                )
                
                if archive_url:
                    tenders = await self.download_and_parse_archive(archive_url)
                    all_tenders.extend(tenders)
                    
                    if len(all_tenders) >= limit:
                        break
            
            except Exception as e:
                logger.warning(f"Error getting tenders for region {reg}: {e}")
                continue
        
        return all_tenders[:limit]
