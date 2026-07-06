"""
Клиент для работы с DeepSeek API для анализа документов
"""
import httpx
import json
from typing import Dict, Optional, List
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

ALLOWED_DEEPSEEK_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro"}


class DeepSeekClient:
    """Клиент для работы с DeepSeek API"""
    
    def __init__(self):
        self.api_url = settings.DEEPSEEK_API_URL
        self.api_key = settings.DEEPSEEK_API_KEY
        self.quick_model = settings.DEEPSEEK_QUICK_MODEL
        self.deep_model = settings.DEEPSEEK_DEEP_MODEL
        self._validate_model(self.quick_model)
        self._validate_model(self.deep_model)

    def _validate_model(self, model: str) -> None:
        if model not in ALLOWED_DEEPSEEK_MODELS:
            allowed = ", ".join(sorted(ALLOWED_DEEPSEEK_MODELS))
            raise ValueError(f"Unsupported DeepSeek model '{model}'. Allowed models: {allowed}")

    def _get_model(self, analysis_type: str) -> str:
        return self.quick_model if analysis_type == "quick" else self.deep_model

    def _prepare_documents_text(self, documents_text: str, limit: int, analysis_type: str) -> str:
        if len(documents_text) <= limit:
            return documents_text

        logger.warning(
            "DeepSeek %s analysis documents text truncated from %s to %s characters",
            analysis_type,
            len(documents_text),
            limit,
        )
        return (
            documents_text[:limit]
            + f"\n\n[ВНИМАНИЕ: текст документов обрезан до {limit} символов из {len(documents_text)}. "
            "Анализ выполнен по части доступного текста.]"
        )
    
    async def analyze_tender_documents(
        self,
        tender_title: str,
        tender_description: str,
        documents_text: str,
        analysis_type: str = "deep"
    ) -> Dict:
        """
        Анализ документов тендера через DeepSeek API
        
        Args:
            analysis_type: 'quick' для поверхностного или 'deep' для глубокого анализа
        
        Возвращает структурированный анализ:
        - summary: краткое описание
        - critical_requirements: критические требования
        - deadlines: анализ сроков
        - financial_info: финансовая информация
        - evaluation_criteria: критерии оценки
        - risks: подводные камни
        """
        
        model = self._get_model(analysis_type)

        if analysis_type == "quick":
            prompt = self._build_quick_analysis_prompt(
                tender_title,
                tender_description,
                documents_text
            )
            max_tokens = 2000  # Увеличиваем для более детального анализа
        else:
            prompt = self._build_deep_analysis_prompt(
                tender_title,
                tender_description,
                documents_text
            )
            max_tokens = 3000
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Ты эксперт по анализу тендерной документации в сфере госзакупок России. Твоя задача - структурированно анализировать документы закупок и выдавать информацию в формате JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": max_tokens
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

                    # Парсим JSON ответ
                    try:
                        # Убираем markdown блоки если есть
                        cleaned_content = self._clean_json_response(content)
                        analysis = json.loads(cleaned_content)
                        return analysis
                    except json.JSONDecodeError:
                        # Если ответ не JSON, пытаемся извлечь структурированную информацию
                        return self._parse_text_response(content)
                else:
                    logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                    return self._get_default_analysis()
        
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            return self._get_default_analysis()
    
    def _build_quick_analysis_prompt(
        self,
        title: str,
        description: str,
        documents_text: str
    ) -> str:
        """Промпт для поверхностного анализа (расширенный быстрый обзор)"""
        prepared_documents_text = self._prepare_documents_text(documents_text, 12000, "quick")
        return f"""
Проведи ПОВЕРХНОСТНЫЙ анализ тендера. Извлеки МАКСИМУМ информации из предоставленных документов.

НАИМЕНОВАНИЕ: {title}
ОПИСАНИЕ: {description}
ДОКУМЕНТЫ: {prepared_documents_text}

ВАЖНО: Внимательно изучи ВСЕ документы и извлеки ВСЕ доступные данные. Не пиши "нужно проверить", если информация есть в документах!

Верни ТОЛЬКО JSON:
{{
    "summary": "Краткое описание закупки (1-2 предложения)",
    "subject": "Детальное описание предмета закупки (что конкретно нужно поставить/сделать, объемы, характеристики)",
    "location": "Точное место поставки/выполнения (адрес, регион)",
    "delivery_deadline": "Срок поставки/выполнения (точная дата)",
    "application_deadline": "Срок подачи заявок (точная дата и время)",
    "financial_info": {{
        "initial_price": "НМЦК (точная сумма с валютой)",
        "guarantee_amount": "Обеспечение заявки (точная сумма или процент от НМЦК, если указано)",
        "contract_guarantee": "Обеспечение исполнения контракта (точная сумма или процент, если указано)",
        "advance": "Аванс (точный процент или сумма, если указано, иначе 'не предусмотрен')",
        "currency": "Валюта",
        "payment_terms": "Условия оплаты (сроки, этапы, если указано)"
    }},
    "basic_requirements": {{
        "licenses_required": "Конкретные лицензии (перечисли все, что указано в документах, или 'не требуются')",
        "sro_required": "Требования к СРО (допуски, если указано)",
        "experience_required": "Требования к опыту (количество контрактов, сумма, период, если указано)",
        "qualification_required": "Требования к квалификации персонала (если указано)",
        "equipment_required": "Требования к оборудованию/технике (если указано)",
        "other_requirements": "Другие требования (если есть)"
    }},
    "delivery_terms": {{
        "delivery_method": "Способ доставки (если указано)",
        "delivery_address": "Адрес доставки (если указано)",
        "packaging_requirements": "Требования к упаковке (если указано)",
        "quality_requirements": "Требования к качеству/стандартам (если указано)"
    }},
    "quick_assessment": {{
        "suitable": "Подходит вам (да/нет/нужно проверить - на основе извлеченных данных)",
        "complexity": "Уровень сложности (низкий/средний/высокий)",
        "key_risks": "Ключевые риски (кратко, 2-3 пункта)",
        "recommendation": "Рекомендация: стоит ли смотреть подробнее и почему"
    }}
}}
"""
    
    def _build_deep_analysis_prompt(
        self,
        title: str,
        description: str,
        documents_text: str
    ) -> str:
        """Промпт для глубокого анализа (полный разбор)"""
        prepared_documents_text = self._prepare_documents_text(documents_text, 15000, "deep")
        return f"""
Проведи ГЛУБОКИЙ анализ тендера. Проанализируй ВСЕ аспекты для принятия решения об участии.

НАИМЕНОВАНИЕ: {title}
ОПИСАНИЕ: {description}
ДОКУМЕНТЫ: {prepared_documents_text}

Верни ТОЛЬКО JSON:
{{
    "summary": "Детальное описание закупки",
    "subject": {{
        "full_list": "Полный перечень товаров/работ",
        "technical_specs": "Технические характеристики",
        "equivalents": "Допускаются ли аналоги (какие бренды)",
        "okpd2_codes": "Коды ОКПД2"
    }},
    "location": {{
        "address": "Адрес поставки/выполнения",
        "region": "Регион",
        "delivery_terms": "Условия доставки"
    }},
    "deadlines": {{
        "application_deadline": "Срок подачи заявок",
        "contract_deadline": "Срок исполнения контракта",
        "is_realistic": true/false,
        "notes": "Замечания по срокам"
    }},
    "financial_analysis": {{
        "initial_price": "НМЦК",
        "price_breakdown": "Разбивка по позициям (если есть)",
        "market_comparison": "Сравнение с рыночными ценами",
        "estimated_cost": "Оценка себестоимости",
        "potential_margin": "Потенциальная маржа (%)",
        "break_even_price": "Точка безубыточности",
        "guarantee_amount": "Обеспечение заявки",
        "contract_guarantee": "Обеспечение контракта",
        "advance": "Аванс (если есть)",
        "payment_terms": "Условия оплаты (этапы, сроки)"
    }},
    "for_construction": {{
        "volumes": "Объемы работ (м², шт, п.м.)",
        "price_per_unit": "Стоимость за единицу",
        "materials": "Список материалов",
        "estimate_analysis": "Анализ сметы"
    }},
    "full_requirements": {{
        "licenses": ["Все лицензии с номерами"],
        "sro": ["Допуски СРО"],
        "experience": "Требования к опыту (контракты, суммы)",
        "personnel": "Требования к персоналу",
        "equipment": "Требуемое оборудование",
        "subcontracting": "Можно ли субподряд"
    }},
    "evaluation_criteria": {{
        "formula": "Формула оценки заявок",
        "price_weight": "Вес цены (%)",
        "non_price_criteria": ["Неценовые критерии с весами"],
        "recommendations": "Рекомендации по заявке"
    }},
    "risks": {{
        "level": "low/medium/high",
        "critical_risks": ["Критические риски"],
        "financial_risks": ["Финансовые риски"],
        "operational_risks": ["Операционные риски"],
        "legal_risks": ["Юридические риски"],
        "hidden_requirements": ["Скрытые требования"]
    }},
    "final_assessment": {{
        "win_probability": "Вероятность победы (%)",
        "recommended_price": "Рекомендуемая цена",
        "profitability": "Рентабельность при разных ценах",
        "recommendation": "Участвовать/Не участвовать/Под вопросом",
        "action_plan": "План действий для участия"
    }}
}}
"""
    
    def _clean_json_response(self, content: str) -> str:
        """Очищает ответ от markdown блоков и лишних символов"""
        import re

        # Убираем ```json ... ``` блоки
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        match = re.search(json_block_pattern, content)
        if match:
            return match.group(1).strip()

        # Если нет блоков, пробуем найти JSON объект
        json_object_pattern = r'\{[\s\S]*\}'
        match = re.search(json_object_pattern, content)
        if match:
            return match.group(0)

        return content

    def _parse_text_response(self, text: str) -> Dict:
        """Парсинг текстового ответа, если JSON не получен"""
        # Простая эвристика для извлечения информации из текста
        return {
            "summary": text[:500] if text else "Анализ не выполнен",
            "critical_requirements": {},
            "deadlines": {},
            "financial_info": {},
            "evaluation_criteria": {},
            "risks": {"level": "medium", "issues": []},
            "margin_analysis": {}
        }
    
    def _get_default_analysis(self) -> Dict:
        """Возвращает анализ по умолчанию при ошибке"""
        return {
            "summary": "Не удалось выполнить анализ",
            "critical_requirements": {},
            "deadlines": {},
            "financial_info": {},
            "evaluation_criteria": {},
            "risks": {
                "level": "medium",
                "issues": ["Ошибка при анализе документов"]
            },
            "margin_analysis": {}
        }
    
    async def calculate_win_probability(
        self,
        tender_data: Dict,
        company_profile: Optional[Dict] = None
    ) -> float:
        """
        Расчет вероятности победы (0-100%)
        
        company_profile может содержать:
        - okpd2_codes: коды ОКПД2 компании
        - licenses: имеющиеся лицензии
        - region: регион компании
        - experience_years: годы опыта
        """
        # Упрощенная логика для MVP
        # В продакшене здесь будет более сложная ML-модель
        
        score = 50.0  # Базовая вероятность
        
        # Проверка соответствия ОКПД2
        if company_profile and tender_data.get("okpd2_codes"):
            company_okpd2 = company_profile.get("okpd2_codes", [])
            tender_okpd2 = tender_data.get("okpd2_codes", [])
            if any(code in company_okpd2 for code in tender_okpd2):
                score += 20
        
        # Проверка региона
        if company_profile and tender_data.get("customer_region"):
            if company_profile.get("region") == tender_data.get("customer_region"):
                score += 15
        
        # Проверка лицензий
        if company_profile and tender_data.get("requirements"):
            company_licenses = company_profile.get("licenses", [])
            required_licenses = tender_data.get("requirements", {}).get("licenses", [])
            if all(lic in company_licenses for lic in required_licenses):
                score += 15
        
        return min(score, 100.0)
