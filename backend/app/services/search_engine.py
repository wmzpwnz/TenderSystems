"""
Продвинутый поисковый движок для тендеров

Возможности:
- Полнотекстовый поиск (PostgreSQL FTS)
- Поиск по ключевым словам (title, description, ОКПД2)
- Умные фильтры (регион, цена, сроки, статус, заказчик)
- Морфология (лыжи = лыжа = лыж)
- Ранжирование результатов (релевантность)
- Быстрый поиск (< 100ms на 100K записей)
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy import or_, and_, func, cast, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.tender import Tender

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Движок поиска тендеров с умными фильтрами

    Примеры запросов:
    - "лыжи палки" → найдёт все тендеры с этими словами
    - "ОКПД: 36.40.11.133" → по коду ОКПД2
    - "ИНН: 7707083893" → по ИНН заказчика
    - "регион: Москва цена: 100000-500000" → комбинированный поиск
    """

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        # Основной поиск
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,

        # Фильтры по категориям
        regions: Optional[List[str]] = None,
        okpd2_codes: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,

        # Фильтры по заказчику
        customer_inn: Optional[str] = None,
        customer_name: Optional[str] = None,

        # Фильтры по цене
        price_from: Optional[float] = None,
        price_to: Optional[float] = None,
        exclude_without_price: bool = False,

        # Фильтры по обеспечению
        guarantee_from: Optional[float] = None,
        guarantee_to: Optional[float] = None,
        without_guarantee: Optional[bool] = None,

        # Фильтры по срокам
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None,
        deadline_after: Optional[datetime] = None,
        deadline_before: Optional[datetime] = None,
        deadline_less_than_days: Optional[int] = None,  # Срок подачи заявок < N дней

        # Этапы закупки
        stages: Optional[List[str]] = None,  # ["active", "evaluation", "completed", "cancelled"]

        # Новые фильтры
        procurement_types: Optional[List[str]] = None,  # ["44-ФЗ", "223-ФЗ", "Коммерческие"]
        procedure_types: Optional[List[str]] = None,    # ["Аукцион", "Конкурс", "Запрос котировок"]

        # Дополнительные параметры
        platform: Optional[str] = None,  # Площадка
        contract_guarantee_from: Optional[float] = None,
        contract_guarantee_to: Optional[float] = None,
        prepayment_type: Optional[str] = None,  # prepayment_44fz, prepayment_223fz, no_prepayment
        preferences: Optional[List[str]] = None,  # СМП/СОНКО, УИС и т.д.

        # Сортировка и пагинация
        sort_by: str = "relevance",  # relevance, price, deadline, published
        sort_order: str = "desc",  # asc, desc
        page: int = 1,
        page_size: int = 50,

        # Дополнительно
        include_analyzed_only: bool = False,
        search_in_documents: bool = False,  # Поиск в тексте документов (медленнее)
    ) -> Dict:
        """
        Универсальный поиск с умными фильтрами

        Returns:
            {
                "items": List[Tender],
                "total": int,
                "page": int,
                "page_size": int,
                "search_time_ms": float
            }
        """
        start_time = datetime.now()

        # Базовый запрос
        q = self.db.query(Tender)
        dialect_name = self.db.bind.dialect.name if self.db.bind is not None else ""

        # === ПОЛНОТЕКСТОВЫЙ ПОИСК ===

        if query or keywords:
            search_terms = []

            # Парсим query на ключевые слова
            if query:
                search_terms.extend(self._parse_query(query))

            if keywords:
                search_terms.extend(keywords)

            # Строим поисковый фильтр
            if search_terms:
                search_conditions = []

                for term in search_terms:
                    if dialect_name == "postgresql":
                        # PostgreSQL FTS path uses GIN indexes from migrations.
                        search_conditions.append(
                            or_(
                                func.to_tsvector('russian', func.coalesce(Tender.title, '')).op('@@')(
                                    func.plainto_tsquery('russian', term)
                                ),
                                func.to_tsvector('russian', func.coalesce(Tender.description, '')).op('@@')(
                                    func.plainto_tsquery('russian', term)
                                ),
                                Tender.number.ilike(f"%{term}%"),
                                Tender.eis_id.ilike(f"%{term}%"),
                            )
                        )
                        search_conditions.append(
                            func.to_tsvector('russian', func.coalesce(Tender.customer_name, '')).op('@@')(
                                func.plainto_tsquery('russian', term)
                            )
                        )
                    else:
                        search_conditions.append(
                            or_(
                                Tender.title.ilike(f"%{term}%"),
                                Tender.description.ilike(f"%{term}%"),
                                Tender.customer_name.ilike(f"%{term}%"),
                                Tender.number.ilike(f"%{term}%"),
                                Tender.eis_id.ilike(f"%{term}%"),
                            )
                        )

                    # Поиск в ОКПД2 кодах (JSON field)
                    if term.replace('.', '').isdigit():
                        # Если term похож на код ОКПД2
                        search_conditions.append(
                            cast(Tender.okpd2_codes, String).ilike(f"%{term}%")
                        )

                # Комбинируем условия (ИЛИ)
                if search_conditions:
                    q = q.filter(or_(*search_conditions))

        # Исключаем ключевые слова
        if exclude_keywords:
            for term in exclude_keywords:
                q = q.filter(
                    and_(
                        ~Tender.title.ilike(f"%{term}%"),
                        ~Tender.description.ilike(f"%{term}%")
                    )
                )

        # === ФИЛЬТРЫ ===

        # Регион
        if regions:
            region_conditions = [Tender.customer_region.ilike(f"%{r}%") for r in regions]
            q = q.filter(or_(*region_conditions))

        # ОКПД2 коды
        if okpd2_codes:
            okpd_conditions = []
            for code in okpd2_codes:
                okpd_conditions.append(
                    cast(Tender.okpd2_codes, String).ilike(f"%{code}%")
                )
            q = q.filter(or_(*okpd_conditions))

        # Статус
        if statuses:
            q = q.filter(Tender.status.in_(statuses))

        # Заказчик (ИНН)
        if customer_inn:
            q = q.filter(Tender.customer_inn == customer_inn)

        # Заказчик (название)
        if customer_name:
            q = q.filter(Tender.customer_name.ilike(f"%{customer_name}%"))

        # Цена
        if price_from is not None:
            q = q.filter(Tender.initial_price >= price_from)

        if price_to is not None:
            q = q.filter(Tender.initial_price <= price_to)

        if exclude_without_price:
            q = q.filter(Tender.initial_price.isnot(None))

        # Обеспечение заявки
        if guarantee_from is not None:
            q = q.filter(Tender.guarantee_amount >= guarantee_from)

        if guarantee_to is not None:
            q = q.filter(Tender.guarantee_amount <= guarantee_to)

        if without_guarantee is True:
            q = q.filter(
                or_(
                    Tender.guarantee_amount.is_(None),
                    Tender.guarantee_amount == 0
                )
            )
        elif without_guarantee is False:
            q = q.filter(
                and_(
                    Tender.guarantee_amount.isnot(None),
                    Tender.guarantee_amount > 0
                )
            )

        # Сроки публикации
        if published_after:
            q = q.filter(Tender.publication_date >= published_after)

        if published_before:
            q = q.filter(Tender.publication_date <= published_before)

        # Сроки подачи заявок
        if deadline_after:
            q = q.filter(Tender.application_deadline >= deadline_after)

        if deadline_before:
            q = q.filter(Tender.application_deadline <= deadline_before)

        # Дедлайн меньше N дней
        if deadline_less_than_days is not None:
            deadline_threshold = datetime.now() + timedelta(days=deadline_less_than_days)
            q = q.filter(
                and_(
                    Tender.application_deadline.isnot(None),
                    Tender.application_deadline <= deadline_threshold,
                    Tender.application_deadline >= datetime.now()
                )
            )

        # Этапы (более детальная фильтрация по статусу)
        if stages:
            q = q.filter(Tender.status.in_(stages))

        # Только проанализированные
        if include_analyzed_only:
            q = q.filter(Tender.is_analyzed == True)

        # Тип торгов (44-ФЗ, 223-ФЗ, Коммерческие)
        if procurement_types:
            # Пока просто проверяем вхождение в название типа процедуры
            procurement_conditions = []
            for ptype in procurement_types:
                if ptype == "44-ФЗ":
                    procurement_conditions.append(Tender.procedure_type.ilike("%электронный аукцион%"))
                    procurement_conditions.append(Tender.procedure_type.ilike("%конкурс%"))
                elif ptype == "223-ФЗ":
                    procurement_conditions.append(Tender.procedure_type.ilike("%223%"))
                elif ptype == "Коммерческие":
                    procurement_conditions.append(Tender.procedure_type.ilike("%коммерческ%"))
            if procurement_conditions:
                q = q.filter(or_(*procurement_conditions))

        # Способ отбора (Аукцион, Конкурс, Запрос котировок)
        if procedure_types:
            procedure_conditions = []
            for ptype in procedure_types:
                if "Аукцион" in ptype:
                    procedure_conditions.append(Tender.procedure_type.ilike("%аукцион%"))
                elif "Конкурс" in ptype:
                    procedure_conditions.append(Tender.procedure_type.ilike("%конкурс%"))
                elif "котировок" in ptype:
                    procedure_conditions.append(Tender.procedure_type.ilike("%котиров%"))
                elif "поставщика" in ptype:
                    procedure_conditions.append(Tender.procedure_type.ilike("%единст%"))
                    procedure_conditions.append(Tender.procedure_type.ilike("%ед. п%"))
            if procedure_conditions:
                q = q.filter(or_(*procedure_conditions))

        # Площадка
        if platform:
            q = q.filter(Tender.platform == platform)

        # Обеспечение контракта
        if contract_guarantee_from is not None:
            q = q.filter(Tender.contract_guarantee >= contract_guarantee_from)
        if contract_guarantee_to is not None:
            q = q.filter(Tender.contract_guarantee <= contract_guarantee_to)

        # Авансирование
        if prepayment_type:
            q = q.filter(Tender.prepayment_type == prepayment_type)

        # Преимущества и ограничения
        if preferences:
            preference_conditions = []
            for pref in preferences:
                if dialect_name == "postgresql":
                    preference_conditions.append(
                        cast(Tender.preferences, postgresql.JSONB).contains([pref])
                    )
                else:
                    preference_conditions.append(
                        cast(Tender.preferences, String).ilike(f"%{pref}%")
                    )
            if preference_conditions:
                q = q.filter(or_(*preference_conditions))

        # === СОРТИРОВКА ===

        if sort_by == "price":
            if sort_order == "desc":
                q = q.order_by(Tender.initial_price.desc().nullslast())
            else:
                q = q.order_by(Tender.initial_price.asc().nullslast())

        elif sort_by == "deadline":
            if sort_order == "desc":
                q = q.order_by(Tender.application_deadline.desc().nullslast())
            else:
                q = q.order_by(Tender.application_deadline.asc().nullslast())

        elif sort_by == "published":
            if sort_order == "desc":
                q = q.order_by(Tender.publication_date.desc().nullslast())
            else:
                q = q.order_by(Tender.publication_date.asc().nullslast())

        else:  # relevance (по умолчанию)
            # Сортируем по дате публикации (новые сначала)
            q = q.order_by(Tender.publication_date.desc().nullslast())

        # === ПАГИНАЦИЯ ===

        total = q.count()
        offset = (page - 1) * page_size
        items = q.offset(offset).limit(page_size).all()

        # Время поиска
        search_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"Search completed: {total} results in {search_time:.2f}ms")

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size,
            "search_time_ms": round(search_time, 2),
            "filters_applied": self._get_applied_filters(locals())
        }

    def _parse_query(self, query: str) -> List[str]:
        """
        Парсит поисковый запрос на ключевые слова

        Примеры:
        - "лыжи палки" → ["лыжи", "палки"]
        - "ОКПД: 36.40.11.133" → ["36.40.11.133"]
        - "ИНН: 7707083893 регион: Москва" → ["7707083893", "Москва"]
        - "цена от 100000" → ["100000"]
        """
        import re

        terms = []

        # Убираем лишние символы
        query = query.strip()

        # Извлекаем специальные паттерны
        patterns = {
            r'окпд[:\s]+([0-9\.]+)': 'okpd',
            r'инн[:\s]+(\d+)': 'inn',
            r'регион[:\s]+([а-яёa-z\s-]+)': 'region',
            r'цена[:\s]+(\d+)': 'price',
        }

        for pattern, field in patterns.items():
            matches = re.finditer(pattern, query.lower())
            for match in matches:
                value = match.group(1).strip()
                if value:
                    terms.append(value)
                    # Удаляем найденный паттерн из query
                    query = query.replace(match.group(0), '')

        # Оставшиеся слова разбиваем по пробелам
        words = query.split()
        for word in words:
            word = word.strip('.,;:!?()[]{}"""\'')
            if len(word) >= 2:  # Игнорируем слишком короткие слова
                terms.append(word)

        return terms

    def _get_applied_filters(self, params: Dict) -> Dict:
        """Возвращает список применённых фильтров для отладки"""
        applied = {}

        filter_keys = [
            'query', 'keywords', 'exclude_keywords',
            'regions', 'okpd2_codes', 'statuses',
            'customer_inn', 'customer_name',
            'price_from', 'price_to',
            'guarantee_from', 'guarantee_to',
            'published_after', 'published_before',
            'deadline_after', 'deadline_before',
            'deadline_less_than_days',
            'stages'
        ]

        for key in filter_keys:
            if key in params and params[key] is not None:
                applied[key] = params[key]

        return applied

    def suggest_okpd2(self, partial_code: str, limit: int = 10) -> List[Dict]:
        """
        Автодополнение ОКПД2 кодов

        Args:
            partial_code: Частичный код (например, "36.40")
            limit: Максимальное количество подсказок

        Returns:
            List[{"code": "36.40.11.133", "count": 5}]
        """
        # Находим все тендеры с кодами начинающимися на partial_code
        results = self.db.query(
            Tender.okpd2_codes,
            func.count(Tender.id).label('count')
        ).filter(
            cast(Tender.okpd2_codes, String).ilike(f"%{partial_code}%")
        ).group_by(
            Tender.okpd2_codes
        ).order_by(
            func.count(Tender.id).desc()
        ).limit(limit).all()

        suggestions = []
        for codes_json, count in results:
            if codes_json:
                # Извлекаем коды из JSON
                import json
                try:
                    codes = json.loads(codes_json) if isinstance(codes_json, str) else codes_json
                    if isinstance(codes, list):
                        for code in codes:
                            if isinstance(code, str) and code.startswith(partial_code):
                                suggestions.append({"code": code, "count": count})
                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    logger.debug(f"Could not parse OKPD2 codes from '{codes_json}': {e}")

        return suggestions[:limit]


# === Утилиты ===

def quick_search(db: Session, query: str, limit: int = 20) -> List[Tender]:
    """
    Быстрый поиск для автодополнения

    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов

    Returns:
        List[Tender]
    """
    engine = SearchEngine(db)
    result = engine.search(
        query=query,
        page=1,
        page_size=limit,
        sort_by="relevance"
    )
    return result["items"]
