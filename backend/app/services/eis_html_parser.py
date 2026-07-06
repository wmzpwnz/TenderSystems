"""
HTML парсер для zakupki.gov.ru (emergency fallback)

Используется только для мгновенного preview конкретного тендера
Быстрее SOAP API (~1-2 сек vs 3-5 сек)

⚠️ ВНИМАНИЕ: Может сломаться при изменении вёрстки сайта!
Поэтому используем только как last resort
"""
import re
import logging
from typing import Optional, Dict
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class EISHTMLParser:
    """
    Парсер карточки тендера с zakupki.gov.ru

    URL формат:
    https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber={eis_id}
    """

    def __init__(self):
        self.base_url = "https://zakupki.gov.ru"
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def parse_tender(self, eis_id: str) -> Optional[Dict]:
        """
        Парсит страницу тендера и извлекает ключевые данные

        Args:
            eis_id: Номер закупки

        Returns:
            Dict с данными тендера или None при ошибке
        """
        try:
            # URL карточки извещения
            url = f"{self.base_url}/epz/order/notice/ea44/view/common-info.html?regNumber={eis_id}"

            logger.debug(f"Parsing HTML: {url}")

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {eis_id}")
                        return None

                    html = await response.text()

            # Парсим HTML
            soup = BeautifulSoup(html, 'html.parser')

            tender = {
                "eis_id": eis_id,
                "number": eis_id,
                "id": eis_id,
                "_source": "html",
                "_parsed_at": datetime.now().isoformat()
            }

            # ОБЪЕКТ ЗАКУПКИ - ищем в правильных местах
            # На zakupki.gov.ru объект закупки может быть в разных местах:
            # 1. В блоке "Предмет закупки" или "Объект закупки"
            # 2. В data-field="purchaseObjectInfo"
            # 3. В таблице с меткой "Предмет закупки"
            
            purchase_object = None
            
            # Вариант 1: Ищем по data-field
            purchase_object_elem = soup.find('div', {'data-field': 'purchaseObjectInfo'}) or \
                                   soup.find('span', {'data-field': 'purchaseObjectInfo'}) or \
                                   soup.find('td', {'data-field': 'purchaseObjectInfo'})
            
            if purchase_object_elem:
                purchase_object = purchase_object_elem.get_text(strip=True)
            
            # Вариант 2: Ищем по тексту "Предмет закупки" или "Объект закупки"
            if not purchase_object:
                # Ищем label "Предмет закупки" или "Объект закупки"
                for label_text in ['Предмет закупки', 'Объект закупки', 'Наименование предмета закупки']:
                    label_elem = soup.find('td', string=re.compile(label_text, re.I)) or \
                                soup.find('th', string=re.compile(label_text, re.I)) or \
                                soup.find('span', string=re.compile(label_text, re.I)) or \
                                soup.find('div', string=re.compile(label_text, re.I))
                    
                    if label_elem:
                        # Берем следующий элемент (значение)
                        value_elem = label_elem.find_next('td') or \
                                    label_elem.find_next('span') or \
                                    label_elem.find_next('div')
                        if value_elem:
                            purchase_object = value_elem.get_text(strip=True)
                            break
            
            # Вариант 3: Ищем в cardMainInfo, но проверяем, что это не способ закупки
            if not purchase_object:
                title_elem = soup.find('div', class_='cardMainInfo')
                if title_elem:
                    title_span = title_elem.find('span', class_='section__title')
                    if title_span:
                        title_text = title_span.get_text(strip=True)
                        # Проверяем, что это не способ закупки
                        if not (title_text.startswith('223-ФЗ') or 
                               title_text.startswith('44-ФЗ') or 
                               title_text.startswith('615 ПП РФ') or
                               'Закупка у единственного' in title_text or
                               'Аукцион' in title_text or
                               'Конкурс' in title_text):
                            purchase_object = title_text
            
            # Сохраняем объект закупки
            if purchase_object:
                tender["purchaseObjectInfo"] = purchase_object
                tender["title"] = purchase_object  # Для совместимости
            
            # СПОСОБ ЗАКУПКИ - ищем отдельно
            procedure_type = None
            
            # Ищем "Способ определения поставщика" или "Способ закупки"
            for label_text in ['Способ определения поставщика', 'Способ закупки', 'Способ определения']:
                label_elem = soup.find('td', string=re.compile(label_text, re.I)) or \
                            soup.find('th', string=re.compile(label_text, re.I)) or \
                            soup.find('span', string=re.compile(label_text, re.I))
                
                if label_elem:
                    value_elem = label_elem.find_next('td') or \
                                label_elem.find_next('span') or \
                                label_elem.find_next('div')
                    if value_elem:
                        procedure_type = value_elem.get_text(strip=True)
                        break
            
            # Если не нашли в таблице, ищем в cardMainInfo (если там способ закупки)
            if not procedure_type:
                title_elem = soup.find('div', class_='cardMainInfo')
                if title_elem:
                    title_span = title_elem.find('span', class_='section__title')
                    if title_span:
                        title_text = title_span.get_text(strip=True)
                        # Если это способ закупки
                        if (title_text.startswith('223-ФЗ') or 
                            title_text.startswith('44-ФЗ') or 
                            title_text.startswith('615 ПП РФ') or
                            'Закупка у единственного' in title_text or
                            'Аукцион' in title_text or
                            'Конкурс' in title_text):
                            procedure_type = title_text
            
            if procedure_type:
                tender["procedureType"] = procedure_type
                tender["procedure_type"] = procedure_type

            # Цена
            price_section = soup.find('div', class_='price')
            if price_section:
                price_text = price_section.get_text(strip=True)
                # Извлекаем число из строки типа "123 456,78 ₽"
                price_match = re.search(r'([\d\s]+(?:,\d+)?)', price_text)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace(',', '.')
                    try:
                        tender["initialPrice"] = float(price_str)
                        tender["price"] = float(price_str)
                    except ValueError:
                        pass

            # Заказчик
            customer_section = soup.find('div', class_='customer')
            if customer_section:
                customer_name = customer_section.find('span', class_='section__title')
                if customer_name:
                    tender["customerName"] = customer_name.get_text(strip=True)

                # ИНН заказчика
                inn_elem = customer_section.find('span', string=re.compile(r'ИНН'))
                if inn_elem:
                    inn_text = inn_elem.find_next('span')
                    if inn_text:
                        tender["customerInn"] = inn_text.get_text(strip=True)

                # Регион (извлекаем из адреса)
                address_elem = customer_section.find('span', string=re.compile(r'Адрес'))
                if address_elem:
                    address_text = address_elem.find_next('span')
                    if address_text:
                        address = address_text.get_text(strip=True)
                        # Пытаемся извлечь регион
                        region = self._extract_region(address)
                        if region:
                            tender["customerRegion"] = region

            # Статус
            status_elem = soup.find('div', class_='status')
            if status_elem:
                status_text = status_elem.get_text(strip=True)
                tender["status"] = self._normalize_status(status_text)

            # Сроки
            dates_section = soup.find_all('div', class_='date')
            for date_div in dates_section:
                label = date_div.find('span', class_='label')
                value = date_div.find('span', class_='value')

                if label and value:
                    label_text = label.get_text(strip=True)
                    date_text = value.get_text(strip=True)

                    # Дата публикации
                    if 'публикации' in label_text.lower():
                        tender["publishDate"] = self._parse_date(date_text)
                        tender["publication_date"] = self._parse_date(date_text)

                    # Дата окончания подачи заявок
                    elif 'окончани' in label_text.lower() and 'заявок' in label_text.lower():
                        tender["applicationDeadline"] = self._parse_date(date_text)
                        tender["application_deadline"] = self._parse_date(date_text)

            # Тип процедуры
            procedure_elem = soup.find('span', string=re.compile(r'Способ определения'))
            if procedure_elem:
                procedure_text = procedure_elem.find_next('span')
                if procedure_text:
                    tender["procedureType"] = procedure_text.get_text(strip=True)

            # ОКПД2 коды
            okpd_section = soup.find_all('div', class_='okpd2')
            if okpd_section:
                okpd_codes = []
                for okpd_div in okpd_section:
                    code_elem = okpd_div.find('span', class_='code')
                    if code_elem:
                        code = code_elem.get_text(strip=True)
                        okpd_codes.append(code)
                if okpd_codes:
                    tender["okpd2Codes"] = okpd_codes
                    tender["okpd2_codes"] = okpd_codes

            # Обеспечение заявки
            guarantee_elem = soup.find('span', string=re.compile(r'Обеспечение заявки'))
            if guarantee_elem:
                guarantee_text = guarantee_elem.find_next('span')
                if guarantee_text:
                    guarantee_str = guarantee_text.get_text(strip=True)
                    guarantee_match = re.search(r'([\d\s]+(?:,\d+)?)', guarantee_str)
                    if guarantee_match:
                        try:
                            guarantee = guarantee_match.group(1).replace(' ', '').replace(',', '.')
                            tender["guaranteeAmount"] = float(guarantee)
                            tender["guarantee_amount"] = float(guarantee)
                        except ValueError:
                            pass

            # Обеспечение контракта
            contract_guarantee_elem = soup.find('span', string=re.compile(r'Обеспечение.*контракта'))
            if contract_guarantee_elem:
                contract_text = contract_guarantee_elem.find_next('span')
                if contract_text:
                    contract_str = contract_text.get_text(strip=True)
                    contract_match = re.search(r'([\d\s]+(?:,\d+)?)', contract_str)
                    if contract_match:
                        try:
                            contract_guarantee = contract_match.group(1).replace(' ', '').replace(',', '.')
                            tender["contractGuarantee"] = float(contract_guarantee)
                            tender["contract_guarantee"] = float(contract_guarantee)
                        except ValueError:
                            pass

            # Площадка (извлекаем из URL или из текста страницы)
            platform = self._extract_platform(soup, url)
            if platform:
                tender["platform"] = platform

            # Авансирование (ищем упоминания аванса)
            prepayment = self._extract_prepayment_type(soup, tender.get("procedureType", ""))
            if prepayment:
                tender["prepayment_type"] = prepayment

            # Преимущества и ограничения (СМП, УИС и т.д.)
            preferences = self._extract_preferences(soup)
            if preferences:
                tender["preferences"] = preferences

            logger.info(f"✓ HTML parsed: {eis_id}, title: {tender.get('title', 'N/A')[:50]}")

            return tender if tender.get("title") else None

        except Exception as e:
            logger.error(f"Error parsing HTML for {eis_id}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def _extract_region(self, address: str) -> Optional[str]:
        """Извлекает регион из адреса"""
        # Список популярных регионов
        regions = {
            'москва': 'Москва',
            'санкт-петербург': 'Санкт-Петербург',
            'московская область': 'Московская область',
            'ленинградская область': 'Ленинградская область',
            'краснодарский край': 'Краснодарский край',
            'свердловская область': 'Свердловская область',
            'тюменская область': 'Тюменская область',
            'новосибирская область': 'Новосибирская область',
            'татарстан': 'Республика Татарстан',
            'башкортостан': 'Республика Башкортостан',
        }

        address_lower = address.lower()

        for key, value in regions.items():
            if key in address_lower:
                return value

        # Если не нашли известный регион, пытаемся найти паттерн "... область" или "... край"
        match = re.search(r'([А-Яа-яё\s]+(?:область|край|республика))', address)
        if match:
            return match.group(1).strip()

        return None

    def _normalize_status(self, status_text: str) -> str:
        """Нормализует статус"""
        status_lower = status_text.lower()

        if 'прием заявок' in status_lower or 'подача заявок' in status_lower:
            return 'active'
        elif 'рассмотрени' in status_lower or 'работа комиссии' in status_lower:
            return 'evaluation'
        elif 'завершен' in status_lower or 'протокол' in status_lower:
            return 'completed'
        elif 'отменен' in status_lower or 'аннулирован' in status_lower:
            return 'cancelled'
        else:
            return 'unknown'

    def _parse_date(self, date_text: str) -> Optional[str]:
        """
        Парсит дату из разных форматов

        Примеры:
        - "02.01.2024 14:00"
        - "02.01.2024"
        - "2 января 2024 г."
        """
        try:
            # Формат: "02.01.2024 14:00"
            match = re.search(r'(\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?)', date_text)
            if match:
                date_str = match.group(1)
                if ':' in date_str:
                    dt = datetime.strptime(date_str, '%d.%m.%Y %H:%M')
                else:
                    dt = datetime.strptime(date_str, '%d.%m.%Y')
                return dt.isoformat()

            # Формат: "2 января 2024"
            months_ru = {
                'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
                'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
                'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
            }

            for month_ru, month_num in months_ru.items():
                if month_ru in date_text.lower():
                    match = re.search(r'(\d{1,2})\s+' + month_ru + r'\s+(\d{4})', date_text.lower())
                    if match:
                        day = match.group(1).zfill(2)
                        year = match.group(2)
                        dt = datetime.strptime(f"{day}.{month_num}.{year}", '%d.%m.%Y')
                        return dt.isoformat()

        except Exception as e:
            logger.debug(f"Error parsing date '{date_text}': {e}")

        return None

    def _extract_platform(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """
        Извлекает площадку из карточки тендера

        Площадки:
        - РТС-тендер (roseltorg)
        - Сбербанк-АСТ (sberbank-ast)
        - ЭТП ГПБ (etp-gpb)
        - ЕЭТП (eetp)
        - Фабрикант (fabricant)
        """
        try:
            # Ищем упоминание площадки в документах или тексте
            platform_patterns = {
                'roseltorg': ['РТС-тендер', 'roseltorg', 'rts-tender'],
                'sberbank-ast': ['Сбербанк-АСТ', 'sberbank-ast', 'sberbankast'],
                'etp-gpb': ['ЭТП ГПБ', 'etp-gpb', 'etpgpb', 'Газпромбанк'],
                'eetp': ['ЕЭТП', 'eetp', 'Единая электронная торговая площадка'],
                'fabricant': ['Фабрикант', 'fabricant'],
                'lot-online': ['Lot-online', 'lot-online', 'Лот Онлайн'],
                'zakazrf': ['Заказ.РФ', 'zakazrf', 'zakaz.rf'],
            }

            # Ищем информацию о площадке в тексте
            platform_section = soup.find('div', class_='platform') or soup.find('span', string=re.compile(r'Площадка|Электронная площадка'))

            if platform_section:
                platform_text = platform_section.get_text()

                for platform_key, patterns in platform_patterns.items():
                    for pattern in patterns:
                        if pattern.lower() in platform_text.lower():
                            return platform_key

            # Если не нашли в явном виде, ищем по всей странице
            page_text = soup.get_text()
            for platform_key, patterns in platform_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in page_text.lower():
                        return platform_key

            return None

        except Exception as e:
            logger.debug(f"Error extracting platform: {e}")
            return None

    def _extract_prepayment_type(self, soup: BeautifulSoup, procedure_type: str) -> Optional[str]:
        """
        Определяет тип авансирования

        Типы:
        - prepayment_44fz: Есть аванс по 44-ФЗ
        - prepayment_223fz: Есть аванс по 223-ФЗ
        - no_prepayment: Без аванса
        """
        try:
            # Проверяем тип закона из процедуры
            is_44fz = '44-ФЗ' in procedure_type or 'Электронный аукцион' in procedure_type or \
                      'Конкурс' in procedure_type or 'Запрос' in procedure_type
            is_223fz = '223-ФЗ' in procedure_type

            # Ищем информацию об авансе
            prepayment_keywords = ['аванс', 'предоплат', 'авансирование']
            page_text = soup.get_text().lower()

            has_prepayment = any(keyword in page_text for keyword in prepayment_keywords)

            # Ищем конкретные упоминания процента аванса
            prepayment_section = soup.find('span', string=re.compile(r'[Аа]ванс|[Пп]редоплат'))
            if prepayment_section:
                prepayment_text = prepayment_section.find_next('span')
                if prepayment_text:
                    text = prepayment_text.get_text().lower()
                    # Если есть упоминание процента или суммы аванса
                    if re.search(r'\d+\s*%|до\s+\d+', text):
                        has_prepayment = True

            # Определяем тип
            if has_prepayment:
                if is_44fz:
                    return 'prepayment_44fz'
                elif is_223fz:
                    return 'prepayment_223fz'
                else:
                    return 'prepayment_44fz'  # По умолчанию
            else:
                return 'no_prepayment'

        except Exception as e:
            logger.debug(f"Error extracting prepayment type: {e}")
            return None

    def _extract_preferences(self, soup: BeautifulSoup) -> Optional[list]:
        """
        Извлекает преимущества и ограничения

        Варианты:
        - smp_sonko: СМП/СОНКО (малый бизнес, социально ориентированные НКО)
        - uis: Учреждения уголовно-исполнительной системы
        - disabled_orgs: Организации инвалидов
        - national_regime: Национальный режим
        """
        try:
            preferences = []
            page_text = soup.get_text().lower()

            # СМП/СОНКО
            smp_keywords = ['малого и среднего предпринимательства', 'смп', 'сонко',
                           'малый бизнес', 'средний бизнес', 'социально ориентированн']
            if any(keyword in page_text for keyword in smp_keywords):
                preferences.append('smp_sonko')

            # УИС
            uis_keywords = ['уголовно-исполнительной системы', 'уис', 'фсин']
            if any(keyword in page_text for keyword in uis_keywords):
                preferences.append('uis')

            # Организации инвалидов
            disabled_keywords = ['организаци инвалидов', 'общественн организаци инвалидов']
            if any(keyword in page_text for keyword in disabled_keywords):
                preferences.append('disabled_orgs')

            # Национальный режим
            national_keywords = ['национальный режим', 'национальному режиму']
            if any(keyword in page_text for keyword in national_keywords):
                preferences.append('national_regime')

            # Ограничения по участию иностранных лиц
            restriction_section = soup.find('span', string=re.compile(r'Ограничени.*участ.*иностранн'))
            if restriction_section:
                restriction_text = restriction_section.find_next('span')
                if restriction_text and 'да' in restriction_text.get_text().lower():
                    if 'national_regime' not in preferences:
                        preferences.append('national_regime')

            return preferences if preferences else None

        except Exception as e:
            logger.debug(f"Error extracting preferences: {e}")
            return None


# Singleton instance
eis_html_parser = EISHTMLParser()
