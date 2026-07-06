import logging
import httpx
import json
import asyncio
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

class AnalysisService:
    """Сервис для AI-анализа тендеров с использованием DeepSeek"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.enabled = bool(self.api_key)

    async def _call_llm(self, prompt: str, system_prompt: str = "Вы — профессиональный эксперт по государственным закупкам (ФЗ-44 и ФЗ-223).") -> Optional[str]:
        """Вспомогательный метод для вызова DeepSeek API"""
        if not self.enabled:
            logger.warning("DeepSeek API is not configured. Falling back to template analysis.")
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    }
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return None

    async def generate_summary(self, tender_data: Dict[str, Any]) -> str:
        """Генерирует краткое резюме тендера"""
        if self.enabled:
            prompt = f"""Проанализируй тендер и дай краткое резюме (3-4 абзаца).
            Данные тендера:
            Название: {tender_data.get('title')}
            Цена: {tender_data.get('initial_price')} {tender_data.get('currency')}
            Аванс: {tender_data.get('prepayment_type')}
            Преимущества: {tender_data.get('preferences')}
            Заказчик: {tender_data.get('customer_name')}
            Регион: {tender_data.get('customer_region')}
            
            Формат вывода: Markdown. Сфокусируйся на выгоде и рисках для поставщика.
            """
            llm_response = await self._call_llm(prompt)
            if llm_response:
                return llm_response

        # Fallback (legacy logic)
        title = tender_data.get('title', 'Тендер')
        prepayment = tender_data.get('prepayment_type', 'не указан')
        
        summary = f"### 🤖 AI-Анализ закупки (Hacker Mode)\n\n"
        summary += f"**Объект:** {title[:200]}...\n\n"
        if prepayment != "Без аванса":
            summary += f"✅ **Аванс:** Предусмотрена выплата {prepayment}.\n"
        else:
            summary += f"⚠️ **Внимание:** Без аванса. Работа за свои.\n"
        
        summary += "---\n*Анализ сформирован автоматически на основе доступных метаданных*"
        return summary

    async def perform_deep_analysis(self, tender_data: Dict[str, Any], documents: List[Dict]) -> Dict[str, Any]:
        """Выполняет глубокий анализ на основе текстов документов"""
        logger.info(f"Starting deep analysis for tender {tender_data.get('eis_id')}")
        
        # 1. Извлекаем тексты из документов (макс 3 документа для экономии токенов)
        texts = []
        for doc in documents[:3]:
            url = doc.get('url') or doc.get('href')
            name = doc.get('name', 'document')
            if url:
                content = await document_service.download_document(url)
                if content:
                    text = document_service.extract_text(content, name)
                    if text:
                        texts.append(f"Файл: {name}\nСодержание (первые 5000 символов):\n{text[:5000]}")

        combined_text = "\n\n---\n\n".join(texts)
        
        if not combined_text:
            return {
                "error": "Не удалось извлечь текст из документов для анализа",
                "risk_matrix": {"financial": "Unknown", "technical": "Unknown", "legal": "Unknown"},
                "checklist": []
            }

        # 2. Формируем промпт для глубокого анализа
        prompt = f"""Ниже представлен текст тендерной документации. 
        Проведи глубокий аудит и верни результат в формате JSON.
        
        СТРУКТУРА JSON:
        {{
            "summary": "Краткий вывод о сложности закупки",
            "risk_matrix": {{
                "financial": "Низкий/Средний/Высокий + пояснение",
                "technical": "Низкий/Средний/Высокий + пояснение",
                "legal": "Низкий/Средний/Высокий + пояснение"
            }},
            "checklist": [
                {{"item": "Название требования", "description": "Что нужно сделать/иметь", "critical": true/false}}
            ],
            "red_flags": ["список подозрительных моментов или 'заточек'"]
        }}

        ТЕКСТ ДОКУМЕНТАЦИИ:
        {combined_text[:15000]}
        """

        llm_response = await self._call_llm(prompt, system_prompt="Вы — аналитик тендерной документации. Ответ строго в формате JSON.")
        
        try:
            # Пытаемся распарсить JSON (бывает, что LLM добавляет ```json ... ```)
            clean_json = llm_response.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                 clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return {
                "summary": llm_response[:500] if llm_response else "Ошибка разбора ответа AI",
                "error": "Failed to parse structured data"
            }

# Синглтон
analysis_service = AnalysisService()
