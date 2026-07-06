"""
Фоновые задачи для анализа тендеров
"""
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.tender import Tender
from app.models.analysis import Analysis
from app.services.deepseek_client import DeepSeekClient
from app.services.document_processor import DocumentProcessor
from app.services.eis_client import EISClient
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="analyze_tender")
def analyze_tender_task(tender_id: int, user_id: int | None = None):
    """
    Фоновая задача для анализа тендера
    
    Выполняется асинхронно через Celery
    """
    # Запускаем асинхронную функцию
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_analyze_tender_async(tender_id, user_id))
    finally:
        loop.close()


async def _analyze_tender_async(tender_id: int, user_id: int | None = None):
    """Асинхронная функция анализа"""
    db = SessionLocal()
    deepseek_client = DeepSeekClient()
    document_processor = DocumentProcessor()
    eis_client = EISClient()
    
    try:
        tender = db.query(Tender).filter(Tender.id == tender_id).first()
        
        if not tender:
            logger.error(f"Tender {tender_id} not found")
            return
        
        # Получаем документы
        documents = await eis_client.get_tender_documents(tender.eis_id)
        
        if not documents:
            logger.warning(f"No documents found for tender {tender_id}")
            return
        
        # Скачиваем и обрабатываем документы
        document_texts = []
        for doc in documents[:5]:
            doc_url = doc.get("url") or doc.get("downloadUrl")
            if doc_url:
                content = await eis_client.download_document(doc_url)
                if content:
                    filename = doc.get("fileName", "document.pdf")
                    text = await document_processor.extract_text(content, filename)
                    if text:
                        document_texts.append(text)
        
        # Анализируем через DeepSeek
        all_documents_text = "\n\n".join(document_texts)
        ai_analysis = await deepseek_client.analyze_tender_documents(
            tender_title=tender.title or "",
            tender_description=tender.description or "",
            documents_text=all_documents_text
        )
        
        # Рассчитываем вероятность победы
        win_probability = await deepseek_client.calculate_win_probability(
            tender_data={
                "okpd2_codes": tender.okpd2_codes or [],
                "customer_region": tender.customer_region,
                "requirements": tender.requirements or {}
            }
        )
        
        # Сохраняем анализ
        analysis = Analysis(
            tender_id=tender_id,
            user_id=user_id,
            summary=ai_analysis.get("summary", ""),
            critical_requirements=ai_analysis.get("critical_requirements", {}),
            deadlines=ai_analysis.get("deadlines", {}),
            financial_info=ai_analysis.get("financial_info", {}),
            evaluation_criteria=ai_analysis.get("evaluation_criteria", {}),
            risks=ai_analysis.get("risks", {}),
            margin_analysis=ai_analysis.get("margin_analysis", {}),
            win_probability=win_probability,
            risk_level=ai_analysis.get("risks", {}).get("level", "medium"),
            raw_ai_response=ai_analysis
        )
        
        db.add(analysis)
        tender.is_analyzed = True
        db.commit()
        
        logger.info(f"Analysis completed for tender {tender_id}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error analyzing tender {tender_id}: {e}")
        raise
    
    finally:
        db.close()
