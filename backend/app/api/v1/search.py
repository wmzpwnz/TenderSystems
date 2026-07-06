"""
API endpoints для продвинутого поиска тендеров
"""
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from app.services.eis_client import EISClient
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import get_db
from app.services.search_engine import SearchEngine, quick_search
from app.schemas.tender import TenderResponse, TenderFilter
from app.api import deps
from app.models.user import User

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Импортируем limiter из core модуля
from app.core.limiter import limiter


class SearchRequest(BaseModel):
    """Расширенный запрос для поиска"""
    # Основной поиск
    query: Optional[str] = Field(None, description="Поисковый запрос (ключевые слова, ОКПД, ИНН)")
    keywords: Optional[List[str]] = Field(None, description="Список ключевых слов")
    exclude_keywords: Optional[List[str]] = Field(None, description="Исключить слова")

    # Фильтры
    regions: Optional[List[str]] = Field(None, description="Регионы (например, ['Москва', 'Санкт-Петербург'])")
    okpd2_codes: Optional[List[str]] = Field(None, description="Коды ОКПД2")
    statuses: Optional[List[str]] = Field(None, description="Статусы")
    customer_inn: Optional[str] = Field(None, description="ИНН заказчика")
    customer_name: Optional[str] = Field(None, description="Название заказчика (частичное совпадение)")

    # Цена
    price_from: Optional[float] = Field(None, description="Цена от")
    price_to: Optional[float] = Field(None, description="Цена до")
    exclude_without_price: bool = Field(False, description="Исключить без цены")

    # Обеспечение
    guarantee_from: Optional[float] = Field(None, description="Обеспечение от")
    guarantee_to: Optional[float] = Field(None, description="Обеспечение до")
    without_guarantee: Optional[bool] = Field(None, description="Только без обеспечения")

    # Сроки
    published_after: Optional[datetime] = Field(None, description="Опубликовано после")
    published_before: Optional[datetime] = Field(None, description="Опубликовано до")
    deadline_after: Optional[datetime] = Field(None, description="Дедлайн после")
    deadline_before: Optional[datetime] = Field(None, description="Дедлайн до")
    deadline_less_than_days: Optional[int] = Field(None, description="Дедлайн меньше N дней")

    # Этапы
    stages: Optional[List[str]] = Field(None, description="Этапы закупки")

    # Новые фильтры
    procurement_types: Optional[List[str]] = Field(None, description="Тип торгов: 44-ФЗ, 223-ФЗ, Коммерческие")
    procedure_types: Optional[List[str]] = Field(None, description="Способ отбора: Аукцион, Конкурс, Запрос котировок")

    # Площадка и дополнительные параметры
    platform: Optional[str] = Field(None, description="Площадка: roseltorg, sberbank-ast, etp-gpb и т.д.")
    contract_guarantee_from: Optional[float] = Field(None, description="Обеспечение контракта от")
    contract_guarantee_to: Optional[float] = Field(None, description="Обеспечение контракта до")
    prepayment_type: Optional[str] = Field(None, description="Авансирование: prepayment_44fz, prepayment_223fz, no_prepayment")
    preferences: Optional[List[str]] = Field(None, description="Преимущества: СМП/СОНКО, УИС, Организации инвалидов и т.д.")

    # Сортировка
    sort_by: str = Field("relevance", description="Сортировка: relevance, price, deadline, published")
    sort_order: str = Field("desc", description="Порядок: asc, desc")

    # Пагинация
    page: int = Field(1, ge=1, description="Номер страницы")
    page_size: int = Field(50, ge=1, le=100, description="Размер страницы")

    # Дополнительно
    include_analyzed_only: bool = Field(False, description="Только с анализом")


class SearchResponse(BaseModel):
    """Ответ на поиск"""
    items: List[TenderResponse]
    total: int
    page: int
    page_size: int
    pages: int
    search_time_ms: float
    filters_applied: dict


class OKPD2Suggestion(BaseModel):
    """Подсказка ОКПД2 кода"""
    code: str
    count: int


@router.post("/advanced", response_model=SearchResponse)
@limiter.limit("10/minute")
async def advanced_search(
    request: Request,
    search_request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_active_subscription),
):
    """
    Продвинутый поиск тендеров

    Поддерживает:
    - Полнотекстовый поиск по ключевым словам
    - Фильтры по регионам, ценам, срокам, заказчикам
    - Умный парсинг запросов ("ОКПД: 36.40", "ИНН: 123456")
    - Исключение ключевых слов
    - Гибкая сортировка
    """
    engine = SearchEngine(db)

    result = engine.search(
        query=search_request.query,
        keywords=search_request.keywords,
        exclude_keywords=search_request.exclude_keywords,
        regions=search_request.regions,
        okpd2_codes=search_request.okpd2_codes,
        statuses=search_request.statuses,
        customer_inn=search_request.customer_inn,
        customer_name=search_request.customer_name,
        price_from=search_request.price_from,
        price_to=search_request.price_to,
        exclude_without_price=search_request.exclude_without_price,
        guarantee_from=search_request.guarantee_from,
        guarantee_to=search_request.guarantee_to,
        without_guarantee=search_request.without_guarantee,
        published_after=search_request.published_after,
        published_before=search_request.published_before,
        deadline_after=search_request.deadline_after,
        deadline_before=search_request.deadline_before,
        deadline_less_than_days=search_request.deadline_less_than_days,
        stages=search_request.stages,
        procurement_types=search_request.procurement_types,
        procedure_types=search_request.procedure_types,
        platform=search_request.platform,
        contract_guarantee_from=search_request.contract_guarantee_from,
        contract_guarantee_to=search_request.contract_guarantee_to,
        prepayment_type=search_request.prepayment_type,
        preferences=search_request.preferences,
        sort_by=search_request.sort_by,
        sort_order=search_request.sort_order,
        page=search_request.page,
        page_size=search_request.page_size,
        include_analyzed_only=search_request.include_analyzed_only
    )

    return SearchResponse(
        items=[TenderResponse.model_validate(t) for t in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        pages=result["pages"],
        search_time_ms=result["search_time_ms"],
        filters_applied=result["filters_applied"]
    )


@router.get("/quick")
async def quick_search_endpoint(
    request: Request,
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    limit: int = Query(20, ge=1, le=50, description="Максимальное количество результатов"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_active_subscription),
):
    """
    Быстрый поиск для автодополнения

    Возвращает только ТОП результатов без детальной фильтрации
    Используется в поисковой строке для live suggestions
    """
    results = quick_search(db, q, limit)

    return {
        "items": [TenderResponse.model_validate(t) for t in results],
        "total": len(results)
    }


@router.get("/autocomplete")
async def autocomplete_endpoint(
    request: Request,
    q: str = Query(..., min_length=2, description="Поисковый запрос для автодополнения"),
    limit: int = Query(10, ge=1, le=20, description="Максимальное количество подсказок"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_active_subscription),
):
    """
    Автодополнение для поисковой строки

    Возвращает список популярных запросов/тендеров, начинающихся с указанного текста.
    Используется для live suggestions в UI.
    
    Пример:
    - q="медицин" → ["медицинское оборудование", "медицинские услуги", ...]
    """
    import json
    from app.core.redis_client import redis_client
    from sqlalchemy import func, or_
    from app.models.tender import Tender
    
    # Проверяем кеш Redis (5 минут)
    cache_key = f"autocomplete:{q.lower()}:{limit}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Ищем по заголовкам тендеров
    query_lower = q.lower()
    
    # ✅ ОПТИМИЗИРОВАННЫЙ ЗАПРОС с триграммами (использует ix_tenders_title_trgm)
    # Использует similarity для fuzzy matching
    suggestions = db.query(
        Tender.title,
        func.count(Tender.id).label('count')
    ).filter(
        # Триграммный поиск (быстрый!) + similarity ranking
        Tender.title.op('%')(q)  # % оператор для триграмм
    ).group_by(
        Tender.title
    ).order_by(
        func.similarity(Tender.title, q).desc(),  # Сортировка по схожести
        func.count(Tender.id).desc()
    ).limit(limit).all()
    
    # Формируем список уникальных подсказок
    autocomplete_list = []
    seen = set()
    
    for title, count in suggestions:
        # Извлекаем релевантные фразы из заголовка
        title_lower = title.lower()
        if query_lower in title_lower:
            # Берем часть заголовка, содержащую запрос, с контекстом
            idx = title_lower.find(query_lower)
            start = max(0, idx - 10)
            end = min(len(title), idx + len(q) + 30)
            suggestion = title[start:end].strip()
            
            # Очищаем от лишних символов в начале/конце
            if suggestion and suggestion not in seen:
                autocomplete_list.append({
                    "text": suggestion,
                    "count": count
                })
                seen.add(suggestion)
    
    # Если подсказок мало, добавляем простые подсказки из заголовков
    if len(autocomplete_list) < limit:
        # ✅ Используем триграммы для дополнительного запроса
        additional = db.query(
            Tender.title
        ).filter(
            Tender.title.op('%')(q)  # Триграммный поиск
        ).distinct().limit(limit - len(autocomplete_list)).all()
        
        for (title,) in additional:
            if title and title.lower() not in seen:
                # Берем первые 50 символов заголовка
                suggestion = title[:50].strip()
                if suggestion:
                    autocomplete_list.append({
                        "text": suggestion,
                        "count": 1
                    })
                    seen.add(title.lower())
    
    result = {
        "suggestions": [item["text"] for item in autocomplete_list[:limit]],
        "total": len(autocomplete_list)
    }
    
    # Кешируем результат на 5 минут (300 секунд)
    redis_client.set(cache_key, json.dumps(result), ex=300)
    
    return result


@router.get("/suggest/okpd2", response_model=List[OKPD2Suggestion])
async def suggest_okpd2(
    code: str = Query(..., min_length=2, description="Частичный код ОКПД2"),
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество подсказок"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_active_subscription),
):
    """
    Автодополнение ОКПД2 кодов

    Возвращает популярные коды начинающиеся на указанную строку

    Пример:
    - code="36.40" → ["36.40.11.133", "36.40.11.134", ...]
    """
    engine = SearchEngine(db)
    suggestions = engine.suggest_okpd2(code, limit)

    return [OKPD2Suggestion(**s) for s in suggestions]


@router.get("/filters/stats")
async def get_filter_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_active_subscription),
):
    """
    Статистика для фильтров (для UI)

    Возвращает:
    - Популярные регионы (топ-20)
    - Популярные ОКПД2 (топ-20)
    - Диапазон цен (мин/макс)
    - Количество по статусам
    """
    from sqlalchemy import func
    from app.models.tender import Tender

    # Популярные регионы
    regions = db.query(
        Tender.customer_region,
        func.count(Tender.id).label('count')
    ).filter(
        Tender.customer_region.isnot(None)
    ).group_by(
        Tender.customer_region
    ).order_by(
        func.count(Tender.id).desc()
    ).limit(20).all()

    # Диапазон цен
    price_stats = db.query(
        func.min(Tender.initial_price).label('min_price'),
        func.max(Tender.initial_price).label('max_price'),
        func.avg(Tender.initial_price).label('avg_price')
    ).filter(
        Tender.initial_price.isnot(None)
    ).first()

    # Количество по статусам
    statuses = db.query(
        Tender.status,
        func.count(Tender.id).label('count')
    ).filter(
        Tender.status.isnot(None)
    ).group_by(
        Tender.status
    ).all()

    return {
        "regions": [{"name": r[0], "count": r[1]} for r in regions],
        "price": {
            "min": float(price_stats.min_price) if price_stats.min_price else 0,
            "max": float(price_stats.max_price) if price_stats.max_price else 0,
            "avg": float(price_stats.avg_price) if price_stats.avg_price else 0
        },
        "statuses": [{"status": s[0], "count": s[1]} for s in statuses],
        "total_tenders": db.query(Tender).count()
    }

@router.post("/eis-live", response_model=Dict[str, Any])
async def search_eis_live(
    filters: TenderFilter,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.require_active_subscription),
) -> Any:
    """
    Прямой поиск в ЕИС (Live Search).
    Минует базу данных, обращается напрямую к API/HTML ЕИС.
    Требует активную платную подписку.
    """
    eis_client = EISClient()
    logger.info(f"User {current_user.email} requested live EIS search with filters: query={filters.query}, region={filters.region}, status={filters.status}, price_from={filters.price_from}, price_to={filters.price_to}, customer_name={filters.customer_name}, platform={filters.platform}, deadline_less_than_days={filters.deadline_less_than_days}, prepayment_type={filters.prepayment_type}, preferences={filters.preferences}, procedure_types={filters.procedure_types}")
    
    # Выполянем поиск
    try:
        results = await eis_client.search_tenders(filters)
        
        # Получаем данные из результата
        items = results.get("items", []) if isinstance(results, dict) else results
        total = results.get("total", len(items)) if isinstance(results, dict) else len(items)
        
        # Обогащаем items для совместимости с UI
        enriched_items = []
        for item in items:
            t = item.copy() if isinstance(item, dict) else item
            
            if not isinstance(t, dict):
                enriched_items.append(t)
                continue
            
            # Добавляем фейковый id для UI (если нет)
            if 'id' not in t:
                # Генерируем int id из eis_id или просто случайный
                eis_id = t.get('eis_id', str(t.get('regNumber', '')))
                if eis_id:
                    t['id'] = abs(hash(str(eis_id))) % 2147483647
                else:
                    t['id'] = abs(hash(str(t.get('title', '')))) % 2147483647
            
            # Маппинг полей из camelCase в snake_case для UI
            # ОБЪЕКТ ЗАКУПКИ - ВАЖНО! Сохраняем отдельно от способа закупки
            
            # Сначала извлекаем purchaseObjectInfo (если есть)
            if 'purchaseObjectInfo' not in t or not t.get('purchaseObjectInfo'):
                # Пытаемся найти объект закупки в разных полях
                purchase_object = (
                    t.get('purchaseObject') or 
                    t.get('purchase_object') or
                    t.get('subject') or
                    t.get('name') or
                    None
                )
                if purchase_object:
                    t['purchaseObjectInfo'] = purchase_object
            
            # Если title - это способ закупки (начинается с 223-ФЗ, 44-ФЗ и т.д.), не используем его как объект
            title = t.get('title', '')
            is_procedure_type = (
                title.startswith('223-ФЗ') or 
                title.startswith('44-ФЗ') or 
                title.startswith('615 ПП РФ') or
                'Закупка у единственного' in title or
                'Аукцион' in title or
                'Конкурс' in title or
                'Запрос котировок' in title or
                'Запрос предложений' in title or
                'Определение поставщика' in title or
                'завершено' in title.lower()
            )
            
            # Если title - способ закупки, а purchaseObjectInfo нет - ищем объект в других местах
            if is_procedure_type and (not t.get('purchaseObjectInfo')):
                # Не используем title как объект закупки
                # Оставляем purchaseObjectInfo пустым или ищем в description
                if t.get('description') and not (
                    t.get('description', '').startswith('223-ФЗ') or 
                    t.get('description', '').startswith('44-ФЗ')
                ):
                    t['purchaseObjectInfo'] = t.get('description')
            
            # Если purchaseObjectInfo нет, но title не способ закупки - используем title
            if not t.get('purchaseObjectInfo') and not is_procedure_type and title:
                t['purchaseObjectInfo'] = title
            
            # Для совместимости: если purchaseObjectInfo есть, используем его как title
            if t.get('purchaseObjectInfo') and not is_procedure_type:
                t['title'] = t['purchaseObjectInfo']
            
            # Цена
            if 'initialPrice' in t and 'initial_price' not in t:
                t['initial_price'] = t.pop('initialPrice')
            elif 'price' in t and 'initial_price' not in t:
                t['initial_price'] = t.pop('price')
            
            # Заказчик
            if 'customer' in t and isinstance(t['customer'], dict):
                t['customer_name'] = t['customer'].get('name') or t['customer'].get('fullName')
                t['customer_region'] = t['customer'].get('region')
                del t['customer']
            elif 'customerName' in t:
                t['customer_name'] = t.pop('customerName')
            if 'customerRegion' in t:
                t['customer_region'] = t.pop('customerRegion')
            
            # Даты
            if 'publishDate' in t:
                t['publication_date'] = t.pop('publishDate')
            if 'applicationDeadline' in t:
                t['application_deadline'] = t.pop('applicationDeadline')
            
            # Статус (если нет, ставим по умолчанию)
            if 'status' not in t:
                t['status'] = 'active'
            
            # Валюта (по умолчанию RUB)
            if 'currency' not in t:
                t['currency'] = 'RUB'
            
            # Другие обязательные поля
            if 'description' not in t:
                t['description'] = None
            if 'customer_inn' not in t:
                t['customer_inn'] = None
            if 'guarantee_amount' not in t:
                t['guarantee_amount'] = None
            if 'contract_guarantee' not in t:
                t['contract_guarantee'] = None
            if 'contract_deadline' not in t:
                t['contract_deadline'] = None
            if 'procedure_type' not in t:
                t['procedure_type'] = None
            if 'documents_url' not in t:
                t['documents_url'] = None
            if 'documents_data' not in t:
                t['documents_data'] = None
            if 'okpd2_codes' not in t:
                t['okpd2_codes'] = None
            if 'requirements' not in t:
                t['requirements'] = None
            if 'is_analyzed' not in t:
                t['is_analyzed'] = False
            if 'platform' not in t:
                t['platform'] = None
            if 'prepayment_type' not in t:
                t['prepayment_type'] = None
            if 'preferences' not in t:
                t['preferences'] = None
            if 'created_at' not in t:
                t['created_at'] = None
            if 'updated_at' not in t:
                t['updated_at'] = None
            
            # Убеждаемся, что number есть
            if 'number' not in t and 'eis_id' in t:
                t['number'] = t['eis_id']
            
            # Убеждаемся, что url есть для Live Search тендеров (если есть eis_id, но нет url)
            if 'url' not in t and 'eis_id' in t:
                t['url'] = f"https://zakupki.gov.ru/epz/order/view/orderInfo.html?regNumber={t['eis_id']}"
            
            # Сохраняем eis_id явно (если есть id как строка, это может быть eis_id)
            if 'eis_id' not in t and 'id' in t and isinstance(t['id'], str) and len(str(t['id'])) > 10:
                t['eis_id'] = str(t['id'])
            
            enriched_items.append(t)

        # Фильтрация результатов по дополнительным фильтрам
        filtered_items = enriched_items
        from datetime import datetime, timedelta
        
        # Фильтр по названию заказчика
        if filters.customer_name:
            customer_name_lower = filters.customer_name.lower()
            filtered_items = [item for item in filtered_items 
                            if item.get('customer_name') and customer_name_lower in item.get('customer_name', '').lower()]
        
        # Фильтр по площадке
        if filters.platform:
            filtered_items = [item for item in filtered_items 
                            if item.get('platform') and filters.platform.lower() in str(item.get('platform', '')).lower()]
        
        # Фильтр по дедлайну (меньше N дней)
        if filters.deadline_less_than_days:
            today = datetime.now().date()
            deadline_threshold = today + timedelta(days=filters.deadline_less_than_days)
            filtered_items = [item for item in filtered_items 
                            if item.get('application_deadline') and 
                            isinstance(item.get('application_deadline'), (str, datetime)) and
                            (isinstance(item['application_deadline'], datetime) and item['application_deadline'].date() <= deadline_threshold or
                             isinstance(item['application_deadline'], str) and datetime.fromisoformat(item['application_deadline'].replace('Z', '+00:00')).date() <= deadline_threshold)]
        
        # Фильтр по обеспечению заявки
        if filters.guarantee_from is not None:
            filtered_items = [item for item in filtered_items 
                            if item.get('guarantee_amount') is not None and 
                            float(item.get('guarantee_amount', 0)) >= float(filters.guarantee_from)]
        if filters.guarantee_to is not None:
            filtered_items = [item for item in filtered_items 
                            if item.get('guarantee_amount') is not None and 
                            float(item.get('guarantee_amount', 0)) <= float(filters.guarantee_to)]
        
        # Фильтр по обеспечению контракта
        if filters.contract_guarantee_from is not None:
            filtered_items = [item for item in filtered_items 
                            if item.get('contract_guarantee') is not None and 
                            float(item.get('contract_guarantee', 0)) >= float(filters.contract_guarantee_from)]
        if filters.contract_guarantee_to is not None:
            filtered_items = [item for item in filtered_items 
                            if item.get('contract_guarantee') is not None and 
                            float(item.get('contract_guarantee', 0)) <= float(filters.contract_guarantee_to)]
        
        # Фильтр по типу авансирования
        if filters.prepayment_type:
            filtered_items = [item for item in filtered_items 
                            if item.get('prepayment_type') and 
                            filters.prepayment_type.lower() in str(item.get('prepayment_type', '')).lower()]
        
        # Фильтр по преимуществам
        if filters.preferences:
            filtered_items = [item for item in filtered_items 
                            if item.get('preferences') and 
                            any(pref in str(item.get('preferences', [])) for pref in filters.preferences)]
        
        # Фильтр по способу отбора (procedure_types)
        if filters.procedure_types:
            filtered_items = [item for item in filtered_items 
                            if item.get('procedure_type') and 
                            any(proc_type.lower() in str(item.get('procedure_type', '')).lower() 
                                for proc_type in filters.procedure_types)]
        
        # Обновляем total после фильтрации
        total = len(filtered_items)
        
        # Получаем pages из результата, если есть
        pages = results.get("pages", 0) if isinstance(results, dict) else 0
        if not pages and total > 0:
            pages = (total + filters.page_size - 1) // filters.page_size if filters.page_size > 0 else 1
        
        return {
            "items": filtered_items,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
            "pages": pages
        }
    except Exception as e:
        logger.error(f"Error in live EIS search: {e}")
        raise HTTPException(
            status_code=502,
            detail="EIS live search is temporarily unavailable"
        )
