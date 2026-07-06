from fastapi import APIRouter
from app.api.v1 import tenders, analysis, company_profile, search, auth, crm, subscriptions

router = APIRouter()

router.include_router(tenders.router, prefix="/tenders", tags=["tenders"])
router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
router.include_router(company_profile.router, prefix="/profile", tags=["company_profile"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(crm.router, prefix="/crm", tags=["crm"])
router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])