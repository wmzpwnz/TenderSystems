from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.user import User
from app.models.search_subscription import SearchSubscription
from app.schemas.search_subscription import SearchSubscriptionCreate, SearchSubscriptionUpdate, SearchSubscriptionResponse
from app.api.deps import require_active_subscription

router = APIRouter()

@router.post("/", response_model=SearchSubscriptionResponse)
def create_subscription(
    subscription: SearchSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Создать новую подписку на поиск"""
    db_subscription = SearchSubscription(
        **subscription.model_dump(),
        user_id=current_user.id
    )
    db.add(db_subscription)
    try:
        db.commit()
        db.refresh(db_subscription)
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error committing subscription: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return db_subscription

@router.get("/", response_model=List[SearchSubscriptionResponse])
def get_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Получить список всех подписок пользователя"""
    return db.query(SearchSubscription).filter(SearchSubscription.user_id == current_user.id).all()

@router.patch("/{subscription_id}", response_model=SearchSubscriptionResponse)
def update_subscription(
    subscription_id: int,
    subscription_update: SearchSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Обновить настройки подписки"""
    db_sub = db.query(SearchSubscription).filter(
        SearchSubscription.id == subscription_id,
        SearchSubscription.user_id == current_user.id
    ).first()
    
    if not db_sub:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    update_data = subscription_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sub, key, value)
    
    try:
        db.commit()
        db.refresh(db_sub)
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error committing subscription update: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return db_sub

@router.delete("/{subscription_id}")
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """Удалить подписку"""
    db_sub = db.query(SearchSubscription).filter(
        SearchSubscription.id == subscription_id,
        SearchSubscription.user_id == current_user.id
    ).first()
    
    if not db_sub:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    db.delete(db_sub)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error committing subscription delete: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    return {"status": "deleted"}
