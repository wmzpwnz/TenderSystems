"""
Pydantic схемы для анализа
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from decimal import Decimal


class AnalysisRequest(BaseModel):
    """Запрос на анализ"""
    tender_id: int
    force_reanalyze: bool = False


class AnalysisResponse(BaseModel):
    """Схема ответа с результатами анализа"""
    id: int
    tender_id: int
    summary: Optional[str] = None
    critical_requirements: Optional[Dict] = None
    deadlines: Optional[Dict] = None
    financial_info: Optional[Dict] = None
    evaluation_criteria: Optional[Dict] = None
    risks: Optional[Dict] = None
    margin_analysis: Optional[Dict] = None
    win_probability: Optional[Decimal] = None
    risk_level: Optional[str] = None
    raw_ai_response: Optional[Dict] = None
    analysis_version: str = "1.0"
    analysis_type: str = "quick"
    documents_analyzed: Optional[List[Dict]] = None
    cost_breakdown: Optional[Dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


