"""
API endpoints для профиля компании
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.company_profile import CompanyProfile
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()


class CompanyProfileCreate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    region: Optional[str] = None
    licenses: Optional[list] = None
    sro_certificates: Optional[list] = None
    experience_contracts: Optional[int] = 0
    experience_sum: Optional[float] = None
    okpd2_codes: Optional[list] = None
    equipment: Optional[list] = None


class CompanyProfileResponse(BaseModel):
    id: int
    name: Optional[str]
    inn: Optional[str]
    region: Optional[str]
    licenses: Optional[list]
    sro_certificates: Optional[list]
    experience_contracts: Optional[int]
    experience_sum: Optional[float]
    okpd2_codes: Optional[list]
    equipment: Optional[list]
    
    class Config:
        from_attributes = True


@router.get("", response_model=CompanyProfileResponse)
async def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить профиль компании текущего пользователя
    """
    profile = db.query(CompanyProfile).filter(
        CompanyProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found. Create one first."
        )
    
    return CompanyProfileResponse.model_validate(profile)


@router.post("", response_model=CompanyProfileResponse)
async def create_or_update_profile(
    profile_data: CompanyProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Создать или обновить профиль компании текущего пользователя
    """
    # Ищем профиль текущего пользователя
    profile = db.query(CompanyProfile).filter(
        CompanyProfile.user_id == current_user.id
    ).first()
    
    if profile:
        # Обновляем существующий
        for key, value in profile_data.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
    else:
        # Создаем новый с привязкой к пользователю
        profile_data_dict = profile_data.model_dump(exclude_unset=True)
        profile_data_dict['user_id'] = current_user.id
        profile = CompanyProfile(**profile_data_dict)
        db.add(profile)
    
    try:
        db.commit()
        db.refresh(profile)
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error committing company profile: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    
    return CompanyProfileResponse.model_validate(profile)


@router.delete("")
async def delete_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Удалить профиль компании текущего пользователя
    """
    profile = db.query(CompanyProfile).filter(
        CompanyProfile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Company profile not found"
        )
    
    try:
        db.delete(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting company profile: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    
    return {"message": "Profile deleted successfully"}









