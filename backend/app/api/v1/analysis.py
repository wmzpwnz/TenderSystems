"""
API endpoints для AI-анализа тендеров
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.models.tender import Tender
from app.models.analysis import Analysis
from app.models.user import User
from app.services.deepseek_client import DeepSeekClient
from app.services.document_processor import DocumentProcessor
from app.services.eis_client import EISClient
from app.schemas.analysis import AnalysisResponse, AnalysisRequest
from app.tasks.analysis_tasks import analyze_tender_task
from app.services.report_service import report_service
from app.schemas.tender import TenderFilter
from app.api.deps import require_active_subscription

logger = logging.getLogger(__name__)

router = APIRouter()
deepseek_client = DeepSeekClient()
document_processor = DocumentProcessor()
eis_client = EISClient()

# Импортируем limiter из core модуля
from app.core.limiter import limiter


def _normalize_risk_level(value: Optional[str]) -> str:
    if not value:
        return "medium"

    normalized = value.strip().lower()

    if any(token in normalized for token in ("low", "низ", "minimal", "миним")):
        return "low"
    if any(token in normalized for token in ("high", "выс", "critical", "крит")):
        return "high"
    return "medium"


@router.post("/{tender_id}", response_model=dict)
async def analyze_tender(
    tender_id: int,
    background_tasks: BackgroundTasks,
    force_reanalyze: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Запустить анализ тендера через DeepSeek AI
    
    Если анализ уже существует и force_reanalyze=False, возвращает существующий анализ.
    Иначе запускает новый анализ в фоне.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    # Проверяем существующий анализ
    if not force_reanalyze:
        existing_analysis = db.query(Analysis).filter(
            Analysis.tender_id == tender_id,
            Analysis.user_id == current_user.id
        ).order_by(Analysis.created_at.desc()).first()
        
        if existing_analysis:
            return AnalysisResponse.model_validate(existing_analysis)
    
    # Запускаем анализ в фоне
    background_tasks.add_task(analyze_tender_task, tender_id, current_user.id)
    
    return {
        "tender_id": tender_id,
        "status": "processing",
        "message": "Analysis started in background"
    }


@router.get("/{tender_id}", response_model=AnalysisResponse)
async def get_analysis(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Получить результат анализа тендера
    """
    analysis = db.query(Analysis).filter(
        Analysis.tender_id == tender_id,
        Analysis.user_id == current_user.id
    ).order_by(Analysis.created_at.desc()).first()
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Start analysis first."
        )
    
    return AnalysisResponse.model_validate(analysis)


@router.post("/quick/{tender_id}", response_model=AnalysisResponse)
@limiter.limit("10/minute")
async def quick_analyze_tender(
    request: Request,
    tender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Поверхностный анализ тендера (15-30 секунд)
    
    Скачивает только ключевые документы (ТЗ, извещение) и делает быстрый обзор.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    try:
        # Получаем профиль компании для сравнения
        from app.models.company_profile import CompanyProfile
        company_profile = db.query(CompanyProfile).filter(
            CompanyProfile.user_id == current_user.id
        ).first()
        
        # Собираем базовую информацию из БД
        tender_info = _build_tender_info(tender)
        
        # Скачиваем больше документов для лучшего анализа
        documents_text = ""
        documents_analyzed = []
        
        try:
            eis_documents = await eis_client.get_tender_documents(tender.eis_id)
            if eis_documents:
                logger.info(f"Found {len(eis_documents)} documents for quick analysis")
                
                # Расширенный список ключевых слов для важных документов
                important_keywords = [
                    'тз', 'техническое', 'задание', 'извещение', 'notice', 'уведомление',
                    'спецификация', 'specification', 'приложение', 'appendix', 'прил',
                    'требования', 'requirements', 'условия', 'conditions', 'договор', 'contract',
                    'протокол', 'protocol', 'смета', 'estimate', 'ведомость', 'statement',
                    'описание', 'description', 'инструкция', 'instruction'
                ]
                
                # Приоритизируем важные документы
                important_docs = []
                other_docs = []
                
                for doc in eis_documents:
                    filename = (doc.get('fileName', '') or '').lower()
                    if any(keyword in filename for keyword in important_keywords):
                        important_docs.append(doc)
                    else:
                        other_docs.append(doc)
                
                # Берем до 10 важных документов + до 5 дополнительных = до 15 документов
                docs_to_process = (important_docs[:10] + other_docs[:5])[:15]
                
                logger.info(f"Processing {len(docs_to_process)} documents for quick analysis")
                
                for doc in docs_to_process:
                    doc_url = doc.get("url") or doc.get("downloadUrl")
                    if doc_url:
                        try:
                            content = await eis_client.download_document(doc_url)
                            if content:
                                filename = doc.get("fileName", "document.pdf")
                                logger.info(f"Extracting text from {filename}")
                                text = await document_processor.extract_text(content, filename)
                                if text:
                                    # Увеличиваем лимит текста до 5000 символов на документ
                                    text_preview = text[:5000] if len(text) > 5000 else text
                                    documents_text += f"\n\n=== {filename} ===\n{text_preview}"
                                    if len(text) > 5000:
                                        documents_text += f"\n[... документ обрезан, всего {len(text)} символов ...]"
                                    
                                    documents_analyzed.append({
                                        "filename": filename,
                                        "size": len(content),
                                        "text_length": len(text),
                                        "has_text": True
                                    })
                                else:
                                    documents_analyzed.append({
                                        "filename": filename,
                                        "size": len(content),
                                        "text_length": 0,
                                        "has_text": False
                                    })
                        except Exception as doc_error:
                            logger.warning(f"Error downloading document {doc.get('fileName')}: {doc_error}")
                            documents_analyzed.append({
                                "filename": doc.get("fileName", "unknown"),
                                "error": str(doc_error),
                                "has_text": False
                            })
                            continue
        except Exception as e:
            logger.warning(f"Error getting documents: {e}")

        # Объединяем информацию
        full_text = tender_info + documents_text

        # Анализируем через DeepSeek (поверхностный анализ)
        # Увеличиваем лимит токенов для более детального анализа
        ai_analysis = await deepseek_client.analyze_tender_documents(
            tender_title=tender.title or "",
            tender_description=tender.description or "",
            documents_text=full_text,
            analysis_type="quick"
        )

        # Рассчитываем вероятность победы с учетом профиля
        company_data = None
        if company_profile:
            company_data = {
                "okpd2_codes": company_profile.okpd2_codes or [],
                "licenses": company_profile.licenses or [],
                "region": company_profile.region,
                "experience_contracts": company_profile.experience_contracts or 0
            }
        
        win_probability = await deepseek_client.calculate_win_probability(
            tender_data={
                "okpd2_codes": tender.okpd2_codes or [],
                "customer_region": tender.customer_region,
                "requirements": tender.requirements or {}
            },
            company_profile=company_data
        )

        # Сохраняем анализ в БД
        analysis = Analysis(
            tender_id=tender_id,
            user_id=current_user.id,
            analysis_type="quick",
            summary=ai_analysis.get("summary", ""),
            critical_requirements=ai_analysis.get("basic_requirements", {}),
            deadlines={
                "application_deadline": ai_analysis.get("application_deadline"),
                "delivery_deadline": ai_analysis.get("delivery_deadline"),
                "delivery_terms": ai_analysis.get("delivery_terms", {}),
                "notes": ai_analysis.get("quick_assessment", {}).get("recommendation", "")
            },
            financial_info=ai_analysis.get("financial_info", {}),
            evaluation_criteria={},
            risks={
                "level": ai_analysis.get("quick_assessment", {}).get("complexity", "medium"),
                "recommendations": ai_analysis.get("quick_assessment", {}).get("recommendation", "")
            },
            margin_analysis={},
            win_probability=win_probability,
            risk_level=_normalize_risk_level(
                ai_analysis.get("quick_assessment", {}).get("complexity")
            ),
            documents_analyzed=documents_analyzed,
            raw_ai_response=ai_analysis
        )

        db.add(analysis)
        tender.is_analyzed = True
        try:
            db.commit()
            db.refresh(analysis)
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing quick analysis: {e}")
            raise HTTPException(status_code=500, detail="Database error")

        return AnalysisResponse.model_validate(analysis)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"Error in quick analysis: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing tender: {str(e)}"
        )


@router.post("/deep/{tender_id}", response_model=AnalysisResponse)
@limiter.limit("5/minute")
async def deep_analyze_tender(
    request: Request,
    tender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Глубокий анализ тендера (2-5 минут)
    
    Скачивает ВСЕ документы, использует OCR для сканов, делает полный анализ.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    try:
        # Получаем профиль компании
        from app.models.company_profile import CompanyProfile
        company_profile = db.query(CompanyProfile).filter(
            CompanyProfile.user_id == current_user.id
        ).first()
        
        # Собираем базовую информацию
        tender_info = _build_tender_info(tender)
        
        # Скачиваем ВСЕ документы
        documents_text = ""
        documents_analyzed = []
        
        try:
            eis_documents = await eis_client.get_tender_documents(tender.eis_id)
            if eis_documents:
                logger.info(f"Downloading {len(eis_documents)} documents for deep analysis")
                
                for doc in eis_documents:
                    doc_url = doc.get("url") or doc.get("downloadUrl")
                    if doc_url:
                        try:
                            content = await eis_client.download_document(doc_url)
                            if content:
                                filename = doc.get("fileName", "document.pdf")
                                logger.info(f"Processing document: {filename}")
                                
                                # Извлекаем текст (с OCR для сканов)
                                text = await document_processor.extract_text(content, filename)
                                if text:
                                    documents_text += f"\n\n=== {filename} ===\n{text}"
                                    documents_analyzed.append({
                                        "filename": filename,
                                        "size": len(content),
                                        "text_length": len(text),
                                        "has_text": len(text.strip()) > 0
                                    })
                                else:
                                    documents_analyzed.append({
                                        "filename": filename,
                                        "size": len(content),
                                        "text_length": 0,
                                        "has_text": False,
                                        "note": "Не удалось извлечь текст"
                                    })
                        except Exception as doc_error:
                            logger.warning(f"Error processing document {doc.get('fileName')}: {doc_error}")
                            documents_analyzed.append({
                                "filename": doc.get("fileName", "unknown"),
                                "error": str(doc_error)
                            })
                            continue
        except Exception as e:
            logger.warning(f"Error getting documents: {e}")

        # Объединяем всю информацию
        full_text = tender_info + documents_text

        # Глубокий анализ через DeepSeek
        logger.info("Starting deep AI analysis...")
        ai_analysis = await deepseek_client.analyze_tender_documents(
            tender_title=tender.title or "",
            tender_description=tender.description or "",
            documents_text=full_text,
            analysis_type="deep"
        )

        # Рассчитываем вероятность победы с учетом профиля
        company_data = None
        if company_profile:
            company_data = {
                "okpd2_codes": company_profile.okpd2_codes or [],
                "licenses": company_profile.licenses or [],
                "region": company_profile.region,
                "experience_contracts": company_profile.experience_contracts or 0,
                "experience_sum": float(company_profile.experience_sum or 0)
            }
        
        win_probability = await deepseek_client.calculate_win_probability(
            tender_data={
                "okpd2_codes": tender.okpd2_codes or [],
                "customer_region": tender.customer_region,
                "requirements": tender.requirements or {}
            },
            company_profile=company_data
        )

        # Извлекаем разбивку по позициям из финансового анализа
        cost_breakdown = {}
        financial = ai_analysis.get("financial_analysis", {})
        if financial.get("price_breakdown"):
            cost_breakdown = financial.get("price_breakdown")

        # Сохраняем анализ в БД
        analysis = Analysis(
            tender_id=tender_id,
            user_id=current_user.id,
            analysis_type="deep",
            summary=ai_analysis.get("summary", ""),
            critical_requirements=ai_analysis.get("full_requirements", {}),
            deadlines=ai_analysis.get("deadlines", {}),
            financial_info=financial,
            evaluation_criteria=ai_analysis.get("evaluation_criteria", {}),
            risks=ai_analysis.get("risks", {}),
            margin_analysis={
                "estimated_cost": financial.get("estimated_cost"),
                "potential_margin": financial.get("potential_margin"),
                "break_even_price": financial.get("break_even_price"),
                "profitability": ai_analysis.get("final_assessment", {}).get("profitability")
            },
            win_probability=win_probability,
            risk_level=_normalize_risk_level(ai_analysis.get("risks", {}).get("level")),
            documents_analyzed=documents_analyzed,
            cost_breakdown=cost_breakdown,
            raw_ai_response=ai_analysis
        )

        db.add(analysis)
        tender.is_analyzed = True
        try:
            db.commit()
            db.refresh(analysis)
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing deep analysis: {e}")
            raise HTTPException(status_code=500, detail="Database error")

        logger.info(f"Deep analysis completed for tender {tender_id}")
        return AnalysisResponse.model_validate(analysis)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        logger.error(f"Error in deep analysis: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in deep analysis: {str(e)}"
        )


@router.post("/{tender_id}/calculate")
async def calculate_profitability(
    tender_id: int,
    proposed_price: float,
    cost: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Калькулятор рентабельности
    
    Рассчитывает маржу и прибыль при заданной цене.
    """
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    initial_price = float(tender.initial_price or 0)
    
    if proposed_price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")
    
    # Если себестоимость не указана, пытаемся оценить из анализа
    if cost is None:
        analysis = db.query(Analysis).filter(
            Analysis.tender_id == tender_id,
            Analysis.user_id == current_user.id,
            Analysis.analysis_type == "deep"
        ).order_by(Analysis.created_at.desc()).first()
        
        if analysis and analysis.margin_analysis:
            estimated_cost = analysis.margin_analysis.get("estimated_cost")
            if estimated_cost:
                # Пытаемся извлечь число из строки
                try:
                    if isinstance(estimated_cost, str):
                        import re
                        cost_match = re.search(r'[\d\s,]+', estimated_cost.replace(' ', '').replace(',', '.'))
                        if cost_match:
                            cost = float(cost_match.group(0))
                    else:
                        cost = float(estimated_cost)
                except (ValueError, AttributeError, TypeError) as e:
                    logger.debug(f"Could not parse estimated_cost '{estimated_cost}': {e}")
    
    # Если все еще нет себестоимости, используем оценку (80% от начальной цены)
    if cost is None:
        cost = initial_price * 0.8
    
    # Расчеты
    profit = proposed_price - cost
    margin_percent = (profit / proposed_price * 100) if proposed_price > 0 else 0
    margin_vs_initial = ((initial_price - proposed_price) / initial_price * 100) if initial_price > 0 else 0
    
    # Обеспечения
    guarantee_amount = float(tender.guarantee_amount or 0)
    contract_guarantee = float(tender.contract_guarantee or 0)
    total_guarantees = guarantee_amount + contract_guarantee
    
    return {
        "tender_id": tender_id,
        "initial_price": initial_price,
        "proposed_price": proposed_price,
        "estimated_cost": cost,
        "profit": profit,
        "margin_percent": round(margin_percent, 2),
        "margin_vs_initial": round(margin_vs_initial, 2),
        "guarantee_amount": guarantee_amount,
        "contract_guarantee": contract_guarantee,
        "total_guarantees": total_guarantees,
        "net_profit_after_guarantees": profit - total_guarantees,
        "break_even_price": cost + total_guarantees,
        "recommendation": _get_price_recommendation(margin_percent, margin_vs_initial)
    }


def _get_price_recommendation(margin_percent: float, margin_vs_initial: float) -> str:
    """Рекомендация по цене"""
    if margin_percent < 5:
        return "Маржа слишком низкая, риск убытков"
    elif margin_percent < 10:
        return "Низкая маржа, участвовать только при уверенности в себестоимости"
    elif margin_percent < 20:
        return "Приемлемая маржа"
    elif margin_vs_initial > -10:
        return "Хорошая маржа, конкурентоспособная цена"
    else:
        return "Высокая маржа, но цена может быть неконкурентоспособной"


@router.get("/{tender_id}/export/pdf")
async def export_analysis_pdf(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Экспорт анализа в PDF
    """
    from fastapi.responses import Response
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from io import BytesIO
    import os

    # Регистрация шрифта для поддержки кириллицы
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    font_name = "Arial"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    else:
        # Пытаемся найти альтернативные пути или используем стандартный (может не поддерживать кириллицу)
        font_name = "Helvetica"
    
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    
    analysis = db.query(Analysis).filter(
        Analysis.tender_id == tender_id,
        Analysis.user_id == current_user.id
    ).order_by(Analysis.created_at.desc()).first()
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Run analysis first."
        )
    
    # Создаем PDF в памяти
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Обновляем шрифты в стилях для кириллицы
    for style in styles.byName.values():
        if hasattr(style, 'fontName'):
            style.fontName = font_name

    # Заголовок
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        fontName=font_name,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30
    )
    story.append(Paragraph(f"Анализ тендера №{tender.number or tender.eis_id}", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Информация о тендере
    story.append(Paragraph(f"<b>Название:</b> {tender.title or 'Не указано'}", styles['Normal']))
    story.append(Paragraph(f"<b>Заказчик:</b> {tender.customer_name or 'Не указан'}", styles['Normal']))
    story.append(Paragraph(f"<b>Цена:</b> {tender.initial_price or 'Не указана'} {tender.currency or 'RUB'}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Результаты анализа
    story.append(Paragraph("<b>Результаты анализа</b>", styles['Heading2']))
    story.append(Spacer(1, 0.3*cm))
    
    if analysis.summary:
        story.append(Paragraph(f"<b>Краткое описание:</b> {analysis.summary}", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
    
    if analysis.win_probability:
        story.append(Paragraph(f"<b>Вероятность победы:</b> {analysis.win_probability}%", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
    
    if analysis.risk_level:
        story.append(Paragraph(f"<b>Уровень риска:</b> {analysis.risk_level}", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
    
    # Финансовая информация
    if analysis.financial_info:
        story.append(Paragraph("<b>Финансовая информация</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))
        fin_info = analysis.financial_info
        if isinstance(fin_info, dict):
            for key, value in fin_info.items():
                if value:
                    story.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
    
    # Риски
    if analysis.risks:
        story.append(Paragraph("<b>Риски и рекомендации</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))
        risks = analysis.risks
        if isinstance(risks, dict):
            if risks.get("issues"):
                story.append(Paragraph("<b>Выявленные риски:</b>", styles['Normal']))
                for issue in risks.get("issues", []):
                    story.append(Paragraph(f"• {issue}", styles['Normal']))
            if risks.get("recommendations"):
                story.append(Paragraph(f"<b>Рекомендации:</b> {risks.get('recommendations')}", styles['Normal']))
    
    # Строим PDF
    doc.build(story)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=analysis_{tender_id}.pdf"
        }
    )


@router.post("/export/excel")
async def export_tenders_excel(
    filters: TenderFilter,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Экспорт результатов поиска в Excel
    """
    # Получаем тендеры по фильтрам (аналогично поиску)
    result = await eis_client.search_tenders(filters)
    tenders = result.get("items", [])
    
    if not tenders:
        raise HTTPException(status_code=404, detail="No tenders found for these filters")
        
    excel_buffer = report_service.generate_tenders_excel(tenders)
    
    from fastapi.responses import Response
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=tenders_export.xlsx"
        }
    )


@router.post("/analyze-by-number/{tender_number}")
async def analyze_by_tender_number(
    tender_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_subscription)
):
    """
    Анализ тендера по номеру закупки.
    Ищет в БД или создаёт запись с базовой информацией.
    """
    # Ищем в БД
    tender = db.query(Tender).filter(
        (Tender.eis_id == tender_number) | (Tender.number == tender_number)
    ).first()

    if not tender:
        # Создаём запись с номером
        tender = Tender(
            eis_id=tender_number,
            number=tender_number,
            title=f"Закупка {tender_number}",
            status="active"
        )
        db.add(tender)
        try:
            db.commit()
            db.refresh(tender)
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing new tender in profitability: {e}")
            raise HTTPException(status_code=500, detail="Database error")

    # Анализируем
    tender_info = _build_tender_info(tender)

    ai_analysis = await deepseek_client.analyze_tender_documents(
        tender_title=tender.title or f"Закупка {tender_number}",
        tender_description=tender.description or "",
        documents_text=tender_info
    )

    win_probability = await deepseek_client.calculate_win_probability(
        tender_data={
            "okpd2_codes": tender.okpd2_codes or [],
            "customer_region": tender.customer_region,
            "requirements": tender.requirements or {}
        }
    )

    analysis = Analysis(
        tender_id=tender.id,
        user_id=current_user.id,
        summary=ai_analysis.get("summary", ""),
        critical_requirements=ai_analysis.get("critical_requirements", {}),
        deadlines=ai_analysis.get("deadlines", {}),
        financial_info=ai_analysis.get("financial_info", {}),
        evaluation_criteria=ai_analysis.get("evaluation_criteria", {}),
        risks=ai_analysis.get("risks", {}),
        margin_analysis=ai_analysis.get("margin_analysis", {}),
        win_probability=win_probability,
        risk_level=_normalize_risk_level(ai_analysis.get("risks", {}).get("level")),
        raw_ai_response=ai_analysis
    )

    db.add(analysis)
    tender.is_analyzed = True
    db.commit()
    db.refresh(analysis)

    return {
        "tender_id": tender.id,
        "tender_number": tender_number,
        "analysis": AnalysisResponse.model_validate(analysis)
    }


def _build_tender_info(tender: Tender) -> str:
    """Собирает всю доступную информацию о тендере в текст"""
    parts = []

    if tender.title:
        parts.append(f"Наименование: {tender.title}")

    if tender.number:
        parts.append(f"Номер закупки: {tender.number}")

    if tender.description:
        parts.append(f"Описание: {tender.description}")

    if tender.customer_name:
        parts.append(f"Заказчик: {tender.customer_name}")

    if tender.customer_inn:
        parts.append(f"ИНН заказчика: {tender.customer_inn}")

    if tender.customer_region:
        parts.append(f"Регион: {tender.customer_region}")

    if tender.initial_price:
        parts.append(f"Начальная цена: {tender.initial_price} {tender.currency or 'RUB'}")

    if tender.guarantee_amount:
        parts.append(f"Обеспечение заявки: {tender.guarantee_amount}")

    if tender.contract_guarantee:
        parts.append(f"Обеспечение контракта: {tender.contract_guarantee}")

    if tender.application_deadline:
        parts.append(f"Срок подачи заявок: {tender.application_deadline}")

    if tender.contract_deadline:
        parts.append(f"Срок исполнения: {tender.contract_deadline}")

    if tender.procedure_type:
        parts.append(f"Способ закупки: {tender.procedure_type}")

    if tender.okpd2_codes:
        parts.append(f"Коды ОКПД2: {', '.join(tender.okpd2_codes)}")

    if tender.requirements:
        req_text = str(tender.requirements)
        parts.append(f"Требования: {req_text[:500]}")

    # Добавляем информацию из documents_data если есть
    if tender.documents_data:
        docs_info = []
        for doc in tender.documents_data[:10]:
            if isinstance(doc, dict):
                doc_name = doc.get('fileName') or doc.get('name', '')
                doc_desc = doc.get('description', '')
                if doc_name:
                    docs_info.append(f"- {doc_name}: {doc_desc}")
        if docs_info:
            parts.append(f"Документы:\n" + "\n".join(docs_info))

    return "\n".join(parts) if parts else "Информация о тендере отсутствует"
