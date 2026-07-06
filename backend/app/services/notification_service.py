import logging
import httpx
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Сервис уведомлений (Telegram, Email и др.)
    """
    def __init__(self):
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        # Дефолтный chat_id для тестов, если не указан у пользователя
        self.default_chat_id = os.getenv("TELEGRAM_DEFAULT_CHAT_ID")

    async def send_telegram_message(self, message: str, chat_id: str = None):
        """Отправить сообщение в Telegram"""
        target_chat = chat_id or self.default_chat_id
        
        if not self.telegram_bot_token or not target_chat:
            # logger.warning("Telegram Bot Token or Chat ID not configured. Message suppressed.")
            # Для отладки в логах
            print(f"\n[TELEGRAM SIMULATOR] To: {target_chat}\n{message}\n")
            return False
            
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json={
                    "chat_id": str(target_chat),
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                })
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Error sending telegram message: {e}")
                return False

    async def notify_new_tenders(self, user_id: int, subscription_name: str, tenders: List[Dict[str, Any]], chat_id: str = None):
        """Уведомить о новых тендерах"""
        if not tenders:
            return
            
        count = len(tenders)
        msg = f"🔔 <b>Новые тендеры по подписке «{subscription_name}»!</b>\n\n"
        msg += f"Всего найдено: <b>{count}</b>\n\n"
        
        # Выводим первые 5 тендеров
        for t in tenders[:5]:
            title = t.get('title', 'Без названия')
            if len(title) > 100:
                title = title[:97] + "..."
            
            price = t.get('initial_price') or t.get('initialPrice')
            price_str = f"{float(price):,.0f} ₽".replace(',', ' ') if price else "Цена не указана"
            
            reg_num = t.get('eis_id') or t.get('number')
            url = t.get('url') or f"https://zakupki.gov.ru/epz/order/view/orderInfo.html?regNumber={reg_num}"
            
            msg += f"📦 <b>{title}</b>\n"
            msg += f"💰 {price_str}\n"
            msg += f"🔗 <a href='{url}'>Открыть в ЕИС</a>\n\n"
            
        if count > 5:
            msg += f"<i>...и еще {count - 5} новых тендеров.</i>"
            
        return await self.send_telegram_message(msg, chat_id)

# Singleton instance
notification_service = NotificationService()
