"""
Клиент для работы с DeepSeek API для анализа документов
"""
import httpx
import json
import re
from typing import Dict, Optional, List
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

ALLOWED_DEEPSEEK_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro"}
DOCUMENT_MARKER_PATTERN = re.compile(r"(?m)^===\s+.+?\s+===\s*$")
SUMMARY_TOKEN_LIMITS = {
    "quick": 1200,
    "deep": 1800,
}
SUMMARY_COMPRESSION_ROUNDS = 3


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

    async def _request_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float = 0.3,
    ) -> str:
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
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )

        if response.status_code != 200:
            raise RuntimeError(f"DeepSeek API error: {response.status_code} - {response.text}")

        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

    async def _prepare_documents_text(self, documents_text: str, limit: int, analysis_type: str) -> str:
        if len(documents_text) <= limit:
            return documents_text

        try:
            return await self._prepare_documents_text_with_chunking(
                documents_text=documents_text,
                limit=limit,
                analysis_type=analysis_type,
            )
        except Exception as exc:
            logger.warning(
                "DeepSeek %s analysis chunking failed, falling back to truncation: %s",
                analysis_type,
                exc,
            )
            return self._truncate_documents_text(documents_text, limit, analysis_type)

    def _truncate_documents_text(self, documents_text: str, limit: int, analysis_type: str) -> str:
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

    async def _prepare_documents_text_with_chunking(
        self,
        documents_text: str,
        limit: int,
        analysis_type: str,
    ) -> str:
        blocks = self._split_documents_text(documents_text)
        if not blocks:
            raise ValueError("No document blocks available for chunking")

        chunks = self._pack_document_blocks(blocks, limit)
        if not chunks:
            raise ValueError("Unable to build document chunks")

        summaries = []
        for index, chunk in enumerate(chunks, start=1):
            summaries.append(
                await self._summarize_chunk_text(
                    chunk_text=chunk,
                    analysis_type=analysis_type,
                    chunk_index=index,
                    total_chunks=len(chunks),
                    stage="document",
                )
            )

        prepared_text = self._format_chunked_context(
            summaries=summaries,
            original_length=len(documents_text),
            total_chunks=len(chunks),
            compression_round=0,
        )

        compression_round = 0
        while len(prepared_text) > limit:
            compression_round += 1
            if compression_round > SUMMARY_COMPRESSION_ROUNDS:
                raise ValueError("Chunk summaries still exceed limit after compression")

            summary_blocks = self._split_section_blocks(prepared_text)
            summary_chunks = self._pack_text_blocks(
                summary_blocks,
                max(limit - 300, limit // 2),
            )
            if not summary_chunks:
                raise ValueError("Unable to build summary compression chunks")

            compressed_summaries = []
            for index, chunk in enumerate(summary_chunks, start=1):
                compressed_summaries.append(
                    await self._summarize_chunk_text(
                        chunk_text=chunk,
                        analysis_type=analysis_type,
                        chunk_index=index,
                        total_chunks=len(summary_chunks),
                        stage="compression",
                    )
                )

            prepared_text = self._format_chunked_context(
                summaries=compressed_summaries,
                original_length=len(documents_text),
                total_chunks=len(chunks),
                compression_round=compression_round,
            )

        return prepared_text

    def _split_documents_text(self, documents_text: str) -> List[str]:
        matches = list(DOCUMENT_MARKER_PATTERN.finditer(documents_text))
        if not matches:
            return self._split_section_blocks(documents_text)

        blocks: List[str] = []
        preamble = documents_text[:matches[0].start()].strip()
        if preamble:
            blocks.extend(self._split_section_blocks(preamble))

        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(documents_text)
            block = documents_text[start:end].strip()
            if block:
                blocks.append(block)

        return blocks

    def _split_section_blocks(self, text: str) -> List[str]:
        sections = [section.strip() for section in re.split(r"\n\s*\n+", text) if section.strip()]
        return sections or ([text.strip()] if text.strip() else [])

    def _pack_document_blocks(self, blocks: List[str], limit: int) -> List[str]:
        fitted_blocks: List[str] = []
        for block in blocks:
            fitted_blocks.extend(self._split_large_block(block, limit))
        return self._pack_text_blocks(fitted_blocks, limit)

    def _split_large_block(self, block: str, limit: int) -> List[str]:
        if len(block) <= limit:
            return [block]

        lines = block.splitlines()
        header = lines[0].strip() if lines and DOCUMENT_MARKER_PATTERN.match(lines[0]) else None
        body = "\n".join(lines[1:]).strip() if header else block.strip()

        body_budget = max(limit - (len(header) + 2 if header else 0), 400)
        sections = self._split_section_blocks(body)
        if len(sections) == 1 and len(sections[0]) == len(body):
            body_chunks = self._split_text_by_length(body, body_budget)
        else:
            body_chunks = self._pack_text_blocks(sections, body_budget)

        if header:
            return [f"{header}\n{chunk}" for chunk in body_chunks if chunk.strip()]
        return body_chunks

    def _pack_text_blocks(self, blocks: List[str], limit: int) -> List[str]:
        chunks: List[str] = []
        current: List[str] = []
        current_length = 0

        for raw_block in blocks:
            block = raw_block.strip()
            if not block:
                continue

            oversized_parts = [block] if len(block) <= limit else self._split_text_by_length(block, limit)

            for part in oversized_parts:
                separator_length = 2 if current else 0
                if current and current_length + separator_length + len(part) > limit:
                    chunks.append("\n\n".join(current))
                    current = [part]
                    current_length = len(part)
                else:
                    current.append(part)
                    current_length += separator_length + len(part)

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def _split_text_by_length(self, text: str, limit: int) -> List[str]:
        text = text.strip()
        if not text:
            return []

        parts: List[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= limit:
                parts.append(remaining.strip())
                break

            split_at = remaining.rfind("\n", 0, limit)
            if split_at < limit // 2:
                split_at = remaining.rfind(" ", 0, limit)
            if split_at < limit // 2:
                split_at = limit

            parts.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        return [part for part in parts if part]

    async def _summarize_chunk_text(
        self,
        chunk_text: str,
        analysis_type: str,
        chunk_index: int,
        total_chunks: int,
        stage: str,
    ) -> str:
        model = self._get_model(analysis_type)
        stage_label = "фрагмент документов" if stage == "document" else "сводку по фрагментам"
        prompt = f"""
Суммаризируй {stage_label} тендерной документации. Сохрани только факты, пригодные для финального анализа.

ОБЯЗАТЕЛЬНО сохрани:
- сроки и даты;
- суммы, проценты, обеспечение, аванс;
- требования к лицензиям, СРО, опыту, персоналу, оборудованию;
- критерии оценки заявок;
- риски, скрытые ограничения, штрафы, обеспечение;
- материалы, объемы, сметные данные, если это стройка;
- любые прямые запреты, ограничения, особенности допуска.

ФРАГМЕНТ {chunk_index}/{total_chunks}:
{chunk_text}

Верни краткую фактологическую сводку без выдуманных выводов. Можно использовать маркеры и короткие списки.
""".strip()

        content = await self._request_completion(
            system_prompt="Ты эксперт по тендерной документации. Сжимаешь документы без потери критически важных фактов.",
            user_prompt=prompt,
            model=model,
            max_tokens=SUMMARY_TOKEN_LIMITS[analysis_type],
            temperature=0.1,
        )
        return content.strip()

    def _format_chunked_context(
        self,
        summaries: List[str],
        original_length: int,
        total_chunks: int,
        compression_round: int,
    ) -> str:
        intro = f"[ВНИМАНИЕ: анализ выполнен по чанкам документов; объем={original_length}; чанков={total_chunks}"
        if compression_round > 0:
            intro += f"; компрессия={compression_round}"
        intro += "]"

        body = "\n\n".join(
            f"[{index}/{len(summaries)}]\n{summary.strip()}"
            for index, summary in enumerate(summaries, start=1)
            if summary.strip()
        )
        return f"{intro}\n\n{body}".strip()
    
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
        document_limit = 12000 if analysis_type == "quick" else 15000
        prepared_documents_text = await self._prepare_documents_text(
            documents_text=documents_text,
            limit=document_limit,
            analysis_type=analysis_type,
        )

        if analysis_type == "quick":
            prompt = self._build_quick_analysis_prompt(
                tender_title,
                tender_description,
                prepared_documents_text
            )
            max_tokens = 2000  # Увеличиваем для более детального анализа
        else:
            prompt = self._build_deep_analysis_prompt(
                tender_title,
                tender_description,
                prepared_documents_text
            )
            max_tokens = 3000
        
        try:
            content = await self._request_completion(
                system_prompt="Ты эксперт по анализу тендерной документации в сфере госзакупок России. Твоя задача - структурированно анализировать документы закупок и выдавать информацию в формате JSON.",
                user_prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=0.3,
            )

            # Парсим JSON ответ
            try:
                # Убираем markdown блоки если есть
                cleaned_content = self._clean_json_response(content)
                analysis = json.loads(cleaned_content)
                return analysis
            except json.JSONDecodeError:
                # Если ответ не JSON, пытаемся извлечь структурированную информацию
                return self._parse_text_response(content)
        
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
        return f"""
Проведи ПОВЕРХНОСТНЫЙ анализ тендера. Извлеки МАКСИМУМ информации из предоставленных документов.

НАИМЕНОВАНИЕ: {title}
ОПИСАНИЕ: {description}
ДОКУМЕНТЫ: {documents_text}

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
        return f"""
Проведи ГЛУБОКИЙ анализ тендера. Проанализируй ВСЕ аспекты для принятия решения об участии.

НАИМЕНОВАНИЕ: {title}
ОПИСАНИЕ: {description}
ДОКУМЕНТЫ: {documents_text}

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
