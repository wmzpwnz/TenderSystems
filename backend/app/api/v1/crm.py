from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.tender import Tender
from app.models.user_tender import UserTender
from app.schemas.crm import FavoriteToggle, CRMStatusUpdate
from app.services.eis_client import EISClient

router = APIRouter()
eis_client = EISClient()

@router.post("/favorites/toggle")
async def toggle_favorite(
    data: FavoriteToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавить/удалить тендер из избранного"""
    # 1. Находим тендер в базе или создаем его
    tender = None
    if data.tender_id.isdigit():
        tender = db.query(Tender).filter(Tender.id == int(data.tender_id)).first()
    
    if not tender:
        # Пробуем найти по eis_id
        tender = db.query(Tender).filter(Tender.eis_id == data.tender_id).first()
    
    if not tender:
        # Пытаемся загрузить из ЕИС и сохранить, чтобы можно было привязать ID
        raw_data = await eis_client.get_tender_details(data.tender_id)
        if raw_data:
            # Убеждаемся, что eis_id установлен
            if 'eis_id' not in raw_data:
                raw_data['eis_id'] = data.tender_id
            
            tender = Tender(**raw_data)
            db.add(tender)
            try:
                db.commit()
                db.refresh(tender)
            except Exception as e:
                db.rollback()
                # Возможно уже был создан параллельно
                tender = db.query(Tender).filter(Tender.eis_id == data.tender_id).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")

    # 2. Проверяем, есть ли уже в избранном
    favorite = db.query(UserTender).filter(
        UserTender.user_id == current_user.id,
        UserTender.tender_id == tender.id
    ).first()

    if favorite:
        db.delete(favorite)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing favorite removal: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        return {"status": "removed", "is_favorite": False}
    else:
        new_fav = UserTender(user_id=current_user.id, tender_id=tender.id, status="saved")
        db.add(new_fav)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error committing favorite addition: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        return {"status": "added", "is_favorite": True}

@router.get("/favorites", response_model=List[dict])
async def get_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список всех избранных тендеров"""
    favorites = db.query(UserTender, Tender).join(Tender).filter(
        UserTender.user_id == current_user.id
    ).all()
    
    result = []
    for fav, tender in favorites:
        # Превращаем модель в словарь, учитывая что Numeric не сериализуется напрямую в некоторых случаях
        t_dict = {c.name: getattr(tender, c.name) for c in tender.__table__.columns}
        t_dict["crm_status"] = fav.status
        t_dict["crm_notes"] = fav.notes
        # Приводим Numeric к float для JSON
        if t_dict.get("initial_price"): t_dict["initial_price"] = float(t_dict["initial_price"])
        if t_dict.get("guarantee_amount"): t_dict["guarantee_amount"] = float(t_dict["guarantee_amount"])
        if t_dict.get("contract_guarantee"): t_dict["contract_guarantee"] = float(t_dict["contract_guarantee"])
        result.append(t_dict)
    
    return result

@router.patch("/favorites/{tender_id}")
async def update_crm_status(
    tender_id: str,
    data: CRMStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить статус или заметки в CRM"""
    tender = db.query(Tender).filter(Tender.eis_id == tender_id).first()
    if not tender and tender_id.isdigit():
        tender = db.query(Tender).filter(Tender.id == int(tender_id)).first()
        
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден в базе")

    favorite = db.query(UserTender).filter(
        UserTender.user_id == current_user.id,
        UserTender.tender_id == tender.id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Тендер не в избранном")

    if data.status:
        favorite.status = data.status
    if data.notes is not None:
        favorite.notes = data.notes
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error committing CRM status update: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return {"status": "updated"}
