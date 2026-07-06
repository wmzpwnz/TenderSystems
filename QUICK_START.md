# Быстрый старт с токеном ЕИС

## Ваши данные

- **Тип потребителя:** Физическое лицо РФ (индивидуальный предприниматель)
- **Токен:** получите в личном кабинете получателя открытых данных ЕИС
- **Тип пользователя:** IP (по умолчанию)

## Настройка .env файла

Создайте файл `.env` в корне проекта и добавьте следующие строки:

```bash
# Токен для физических лиц (ИП)
EIS_SOAP_TOKEN=your_eis_soap_token_here

# Тип пользователя: IP (физическое лицо/ИП)
EIS_SOAP_USER_TYPE=IP

# Использовать SOAP API
EIS_USE_SOAP=true

# Использовать HTML парсинг как fallback
EIS_USE_HTML_PARSING=true
```

## Проверка работы

После настройки `.env` файла, запустите тест:

```bash
# В Docker
docker-compose exec backend python -m pytest backend/tests/test_soap_api.py -v

# Или локально
cd backend
python -m pytest tests/test_soap_api.py -v
```

## Использование в коде

Токен автоматически используется при создании SOAP клиента:

```python
from app.services.eis_soap_client import EISSOAPClient

# Клиент автоматически использует токен из EIS_SOAP_TOKEN
# и тип пользователя IP (по умолчанию)
client = EISSOAPClient()  # Использует EIS_SOAP_TOKEN и user_type='IP'

# Или явно указать токен и тип
client = EISSOAPClient(
    token="your_eis_soap_token_here",
    user_type='IP'
)
```

## Важно

- Токен используется для сервиса **getDocsIP** (для физических лиц)
- URL сервиса: `https://int.zakupki.gov.ru/eis-integration/services/getDocsIP`
- Токен получается через ЕСИА в личном кабинете получателя открытых данных

## Дополнительная информация

- [Полная инструкция по получению токена](EIS_TOKEN_SETUP.md)
- [Документация API](README.md)




