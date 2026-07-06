"""
Отладочный скрипт для проверки реального ответа SOAP API

⚠️ ВАЖНО: С 01.01.2025 используются новые URL сервисов:
- getDocsIP (ФЛ): https://int.zakupki.gov.ru/eis-integration/services/getDocsIP
- getDocsLE (ЮЛ): https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE
"""
import uuid
import datetime
import requests
import xmltodict
import json
import os

token = os.getenv("EIS_SOAP_TOKEN", "")
if not token:
    raise RuntimeError("EIS_SOAP_TOKEN is required")
# Новый URL для физических лиц (с 01.01.2025)
base_url = "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP"

# Формируем SOAP запрос
generated_uuid = str(uuid.uuid4())
generated_datetime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://zakupki.gov.ru/fz44/get-docs-ip/ws">
    <soapenv:Header>
        <individualPerson_token>{token}</individualPerson_token>
    </soapenv:Header>
    <soapenv:Body>
        <ws:getDocsByOrgRegionRequest>
            <index>
                <id>{generated_uuid}</id>
                <createDateTime>{generated_datetime}</createDateTime>
                <mode>PROD</mode>
            </index>
            <selectionParams>
                <orgRegion>77</orgRegion>
                <subsystemType>PRIZ</subsystemType>
                <documentType44>epNotificationEF2020</documentType44>
                <periodInfo>
                    <exactDate>2024-12-26</exactDate>
                </periodInfo>
            </selectionParams>
        </ws:getDocsByOrgRegionRequest>
    </soapenv:Body>
</soapenv:Envelope>"""

print("Отправляем SOAP запрос...")
print(f"URL: {base_url}")
print("Токен: найден в окружении")
print()

headers = {
    'Content-Type': 'text/xml; charset=utf-8',
}

response = requests.post(
    base_url,
    data=xml_data.encode('utf-8'),
    headers=headers,
    timeout=30
)

print(f"Статус ответа: {response.status_code}")
print()

if response.status_code == 200:
    print("Ответ сервера:")
    print("=" * 60)
    print(response.text.replace(token, "[REDACTED]")[:2000])  # Первые 2000 символов
    print("=" * 60)
    print()
    
    try:
        parsed = xmltodict.parse(response.content)
        print("Структура ответа (JSON):")
        print("=" * 60)
        parsed_text = json.dumps(parsed, indent=2, ensure_ascii=False).replace(token, "[REDACTED]")
        print(parsed_text[:2000])
        print("=" * 60)
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
else:
    print(f"Ошибка: {response.status_code}")
    print(response.text.replace(token, "[REDACTED]"))






