"""
API endpoints для работы с тендерами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.tender import Tender
from app.models.analysis import Analysis
from app.services.eis_client import EISClient
from app.services.analysis_service import analysis_service
from app.services.competitor_service import competitor_service
from app.schemas.tender import TenderResponse, TenderListResponse, TenderCreate, TenderFilter
from app.schemas.analysis import AnalysisResponse
from app.models.user import User
from app.models.user_tender import UserTender
from app.api.deps import get_current_user, require_active_subscription

router = APIRouter()
eis_client = EISClient()


@router.post("/{tender_id}/analyze", response_model=dict)
async def analyze_tender(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Запустить AI-анализ тендера (Краткий)
    """
    # ... получение данных тендера
    tender = None
    if tender_id.isdigit():
        tender = db.query(Tender).filter(Tender.id == int(tender_id)).first()
    if not tender:
        tender = db.query(Tender).filter(Tender.eis_id == tender_id).first()
    
    if tender:
        tender_data = tender.__dict__
    else:
        # Загружаем из ЕИС если нет в базе
        detail_data = await eis_client.get_tender_details(tender_id)
        tender_data = eis_client.parse_tender_data(detail_data)

    if not tender_data:
        raise HTTPException(status_code=404, detail="Тендер не найден")

    # Генерируем краткий анализ
    summary = await analysis_service.generate_summary(tender_data)
    
    # Если тендер в базе, помечаем как проанализированный
    if tender:
        tender.is_analyzed = True
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing tender analysis: {e}")
            raise HTTPException(status_code=500, detail="Database error")

    return {
        "tender_id": tender_id,
        "summary": summary,
        "status": "completed"
    }

@router.post("/{tender_id}/deep-analyze", response_model=dict)
async def deep_analyze_tender(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Запустить ГЛУБОКИЙ AI-анализ тендера (с чтением документов)
    """
    tender = None
    if tender_id.isdigit():
        tender = db.query(Tender).filter(Tender.id == int(tender_id)).first()
    if not tender:
        tender = db.query(Tender).filter(Tender.eis_id == tender_id).first()
    
    if not tender:
        # Для глубокого анализа тендер ДОЛЖЕН быть в базе (или мы его создаем)
        detail_data = await eis_client.get_tender_details(tender_id)
        tender_data = eis_client.parse_tender_data(detail_data)
        tender = Tender(**tender_data)
        db.add(tender)
        try:
            db.commit()
            db.refresh(tender)
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing new tender: {e}")
            raise HTTPException(status_code=500, detail="Database error")

    # Получаем документы
    if not tender.documents_data:
        tender.documents_data = await eis_client.get_tender_documents(tender.eis_id)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing documents: {e}")
            raise HTTPException(status_code=500, detail="Database error")

    # Запускаем глубокий анализ
    result = await analysis_service.perform_deep_analysis(tender.__dict__, tender.documents_data)
    
    # Сохраняем результат
    tender.deep_analysis_result = result
    tender.is_analyzed = True
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error committing deep analysis: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    return result

@router.get("/customer/{inn}/intelligence", response_model=dict)
async def get_customer_intelligence(
    inn: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Получить аналитическую справку по заказчику (конкуренты, падение цены)
    """
    return await competitor_service.get_customer_intelligence(inn)


@router.post("/search", response_model=TenderListResponse)
async def search_tenders(
    filters: TenderFilter,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Поиск тендеров (с поддержкой сложных фильтров)
    """
    result = await eis_client.search_tenders(filters)
    
    # Обогащаем результаты информацией об избранном
    items = result.get("items", [])
    if items:
        fav_data = db.query(Tender.eis_id, UserTender.status).join(
            UserTender, Tender.id == UserTender.tender_id
        ).filter(UserTender.user_id == current_user.id).all()
        
        fav_map = {f.eis_id: f.status for f in fav_data}
        
        for item in items:
            eis_id = item.get("eis_id")
            if eis_id in fav_map:
                item["is_favorite"] = True
                item["crm_status"] = fav_map[eis_id]
            else:
                item["is_favorite"] = False
                item["crm_status"] = None
                
    return result


@router.get("/{tender_id}", response_model=TenderResponse)
async def get_tender(
    tender_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Получить детальную информацию о тендере
    
    Поддерживает:
    - Числовой ID из БД (для тендеров в базе)
    - eis_id (для тендеров из Live Search)
    """
    # Пробуем найти по числовому ID (тендер в БД)
    if tender_id.isdigit():
        tender = db.query(Tender).filter(Tender.id == int(tender_id)).first()
        if tender:
            response_data = TenderResponse.model_validate(tender).model_dump()
            # Проверяем избранное
            favorite = db.query(UserTender).filter(
                UserTender.user_id == current_user.id,
                UserTender.tender_id == tender.id
            ).first()
            if favorite:
                response_data["is_favorite"] = True
                response_data["crm_status"] = favorite.status
            return response_data
    
    # Пробуем найти по eis_id (тендер в БД)
    tender = db.query(Tender).filter(Tender.eis_id == tender_id).first()
    if tender:
        response_data = TenderResponse.model_validate(tender).model_dump()
        # Проверяем избранное
        favorite = db.query(UserTender).filter(
            UserTender.user_id == current_user.id,
            UserTender.tender_id == tender.id
        ).first()
        if favorite:
            response_data["is_favorite"] = True
            response_data["crm_status"] = favorite.status
        return response_data
    
    # Если не найден в БД, загружаем из ЕИС (Live Search тендер)
    try:
        logger = logging.getLogger(__name__)
        logger.info(f"Loading tender {tender_id} from EIS (not in DB)")
        
        # Загружаем детальную информацию из ЕИС
        detail_data = await eis_client.get_tender_details(tender_id)
        if detail_data:
            # Парсим данные
            parsed_data = eis_client.parse_tender_data(detail_data)
            
            # Маппинг полей
            tender_dict = {
                "id": abs(hash(str(tender_id))) % 2147483647,  # Генерируем числовой ID
                "eis_id": tender_id,
                # ... остальные поля из parsed_data
                "number": parsed_data.get("number") or tender_id,
                "title": parsed_data.get("title") or parsed_data.get("purchaseObjectInfo") or "Тендер",
                "description": parsed_data.get("description"),
                "customer_name": parsed_data.get("customer_name") or parsed_data.get("customerName"),
                "customer_inn": parsed_data.get("customer_inn") or parsed_data.get("customerInn"),
                "customer_region": parsed_data.get("customer_region") or parsed_data.get("customerRegion"),
                "initial_price": parsed_data.get("initial_price") or parsed_data.get("price") or parsed_data.get("initialPrice"),
                "currency": parsed_data.get("currency", "RUB"),
                "guarantee_amount": parsed_data.get("guarantee_amount") or parsed_data.get("guaranteeAmount"),
                "contract_guarantee": parsed_data.get("contract_guarantee") or parsed_data.get("contractGuarantee"),
                "publication_date": parsed_data.get("publication_date") or parsed_data.get("publishDate"),
                "application_deadline": parsed_data.get("application_deadline") or parsed_data.get("applicationDeadline"),
                "contract_deadline": parsed_data.get("contract_deadline") or parsed_data.get("contractDeadline"),
                "status": parsed_data.get("status", "active"),
                "procedure_type": parsed_data.get("procedure_type") or parsed_data.get("procedureType"),
                "documents_url": parsed_data.get("documents_url") or parsed_data.get("url"),
                "documents_data": parsed_data.get("documents_data") or parsed_data.get("documents"),
                "okpd2_codes": parsed_data.get("okpd2_codes") or parsed_data.get("okpd2Codes"),
                "requirements": parsed_data.get("requirements"),
                "platform": parsed_data.get("platform"),
                "prepayment_type": parsed_data.get("prepayment_type"),
                "preferences": parsed_data.get("preferences"),
                "is_analyzed": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Проверяем избранное в базе, если вдруг по eis_id мы его уже сохраняли
            db_tender = db.query(Tender).filter(Tender.eis_id == tender_id).first()
            if db_tender:
                favorite = db.query(UserTender).filter(
                    UserTender.user_id == current_user.id,
                    UserTender.tender_id == db_tender.id
                ).first()
                if favorite:
                    tender_dict["is_favorite"] = True
                    tender_dict["crm_status"] = favorite.status
            
            return TenderResponse(**tender_dict)
        else:
            raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found in EIS")
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading tender {tender_id} from EIS: {e}")
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")


@router.post("/sync", response_model=List[TenderResponse])
async def sync_tenders_from_eis(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    filters: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Синхронизация тендеров из ЕИС
    
    Загружает новые тендеры из API ЕИС и сохраняет в БД
    """
    try:
        # Получаем данные из ЕИС
        eis_data = await eis_client.search_tenders(
            filters=TenderFilter(**(filters or {}))
        )
        
        if not eis_data or "items" not in eis_data:
            return []
        
        synced_tenders = []
        
        for item in eis_data.get("items", []):
            try:
                # Данные уже обработаны в search_tenders через parse_tender_data
                # Используем их напрямую
                tender_data = item
                
                # Пропускаем тендеры без ID
                if not tender_data.get("eis_id"):
                    continue
                
                # Проверяем, существует ли уже такой тендер
                existing = db.query(Tender).filter(
                    Tender.eis_id == tender_data["eis_id"]
                ).first()
                
                if existing:
                    # Обновляем существующий
                    # Обновляем все поля, заполняя пустые (NULL) значения
                    updated = False
                    for key, value in tender_data.items():
                        # Обновляем если новое значение не None
                        if value is not None:
                            current_value = getattr(existing, key, None)
                            # Обновляем если значение изменилось или было NULL
                            if current_value != value:
                                setattr(existing, key, value)
                                updated = True
                    
                    # Если у тендера пустые поля, загружаем детальную информацию
                    if (not existing.customer_name or not existing.customer_region or 
                        not existing.initial_price or not existing.publication_date):
                        try:
                            detail_data = await eis_client.get_tender_details(existing.eis_id)
                            if detail_data:
                                detail_parsed = eis_client.parse_tender_data(detail_data)
                                for key, value in detail_parsed.items():
                                    if value is not None:
                                        current_value = getattr(existing, key, None)
                                        if current_value is None or current_value != value:
                                            setattr(existing, key, value)
                                            updated = True
                        except Exception as e:
                            logger.debug(f"Error loading details for {existing.eis_id}: {e}")
                    
                    if updated:
                        existing.updated_at = datetime.utcnow()
                    synced_tenders.append(existing)
                else:
                    # Создаем новый
                    new_tender = Tender(**tender_data)
                    db.add(new_tender)
                    synced_tenders.append(new_tender)
            except Exception as e:
                # Логируем ошибку, но продолжаем обработку остальных тендеров
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error processing tender item: {e}")
                continue
        
        try:
            db.commit()
            # Обновляем ID для возврата
            for tender in synced_tenders:
                db.refresh(tender)
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing synced tenders: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        
        return [TenderResponse.model_validate(t) for t in synced_tenders]
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error syncing tenders: {str(e)}")


@router.post("/refresh", response_model=dict)
async def refresh_existing_tenders(
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Принудительное обновление существующих тендеров из ЕИС
    
    Обновляет тендеры с пустыми полями (NULL значениями)
    """
    try:
        # Находим тендеры с пустыми полями
        tenders_to_update = db.query(Tender).filter(
            (Tender.customer_name.is_(None)) |
            (Tender.customer_region.is_(None)) |
            (Tender.initial_price.is_(None)) |
            (Tender.publication_date.is_(None))
        ).limit(limit).all()
        
        if not tenders_to_update:
            return {
                "message": "Нет тендеров для обновления",
                "updated": 0,
                "total": 0
            }
        
        updated_count = 0
        
        # Для каждого тендера загружаем детальную информацию через HTML парсинг
        import logging
        logger = logging.getLogger(__name__)
        
        for tender in tenders_to_update:
            try:
                logger.info(f"Loading details for tender {tender.eis_id}")
                # Загружаем детальную информацию через HTML парсинг
                detail_data = await eis_client.get_tender_details(tender.eis_id)
                if detail_data:
                    detail_parsed = eis_client.parse_tender_data(detail_data)
                    
                    # Обновляем пустые поля
                    updated = False
                    updated_fields = []
                    for key, value in detail_parsed.items():
                        if value is not None:
                            current_value = getattr(tender, key, None)
                            # Обновляем если значение было NULL или изменилось
                            if current_value is None or (key in ['customer_name', 'customer_region', 'initial_price', 'publication_date', 'application_deadline'] and current_value != value):
                                setattr(tender, key, value)
                                updated = True
                                updated_fields.append(key)
                    
                    if updated:
                        tender.updated_at = datetime.utcnow()
                        updated_count += 1
                        logger.info(f"Updated tender {tender.eis_id}, fields: {updated_fields}")
                    else:
                        logger.debug(f"No updates for tender {tender.eis_id}")
                else:
                    logger.warning(f"No detail data for tender {tender.eis_id}")
                        
            except Exception as e:
                logger.warning(f"Error updating tender {tender.eis_id}: {e}")
                continue
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing refreshed tenders: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        
        return {
            "message": f"Обновлено {updated_count} из {len(tenders_to_update)} тендеров",
            "updated": updated_count,
            "total": len(tenders_to_update)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error refreshing tenders: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing tenders: {str(e)}")


@router.delete("/all", response_model=dict)
async def delete_all_tenders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удаляет все тендеры из базы данных
    """
    if not current_user.is_superuser:
         raise HTTPException(status_code=403, detail="Not authorized")
         
    try:
        # Удаляем все анализы, связанные с тендерами
        db.query(Analysis).delete()
        
        # Удаляем все тендеры
        deleted_count = db.query(Tender).delete()
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing delete all tenders: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        
        return {
            "message": f"Удалено {deleted_count} тендеров",
            "deleted": deleted_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")


@router.get("/{tender_id}/documents")
async def get_tender_documents(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Получить список документов тендера
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Если документы не загружены, получаем из ЕИС
    if not tender.documents_data:
        eis_documents = await eis_client.get_tender_documents(tender.eis_id)
        tender.documents_data = eis_documents
        db.commit()
    
    return {
        "tender_id": tender_id,
        "documents": tender.documents_data or []
    }
