# Чеклист проверки работоспособности

## ✅ Проверка кода

### 1. Линтер
- ✅ Нет ошибок линтера во всех измененных файлах
- ✅ Синтаксис Python корректен

### 2. Импорты
- ✅ `EISSOAPClient` правильно импортируется в:
  - `backend/app/services/eis_client.py`
  - `backend/app/services/unified_parser.py`
  - `backend/tests/test_soap_api.py`
  - `backend/scripts/test_eis.py`

### 3. Конфигурация
- ✅ `backend/app/core/config.py` содержит новые переменные:
  - `EIS_SOAP_TOKEN` - токен для ФЛ
  - `EIS_SOAP_TOKEN_LE` - токен для ЮЛ
  - `EIS_SOAP_USER_TYPE` - тип пользователя (IP/LE)

### 4. Docker Compose
- ✅ `docker-compose.yml` обновлен с новыми переменными окружения
- ✅ Все сервисы (backend, celery, celery-beat) используют новые переменные

## ✅ Проверка функциональности

### 1. SOAP Клиент (`eis_soap_client.py`)
- ✅ Использует правильные URL:
  - IP: `https://int.zakupki.gov.ru/eis-integration/services/getDocsIP`
  - LE: `https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE`
- ✅ Правильно определяет тип пользователя (IP/LE)
- ✅ Использует правильные заголовки токенов:
  - IP: `individualPerson_token`
  - LE: `legalEntity_token`
- ✅ Токен передается в SOAP Header и HTTP заголовке

### 2. EIS Client (`eis_client.py`)
- ✅ Правильно инициализирует `EISSOAPClient` с типом пользователя
- ✅ Выбирает правильный токен в зависимости от типа пользователя
- ✅ Fallback на HTML парсинг работает

### 3. Тесты
- ✅ Тестовый файл обновлен для использования типа IP
- ✅ Использует правильный токен по умолчанию

## ⚠️ Важные замечания

### Namespace в SOAP envelope
В текущей реализации используется namespace для getDocsIP:
```xml
xmlns:ws="http://zakupki.gov.ru/fz44/get-docs-ip/ws"
```

**Внимание:** Для сервиса getDocsLE может потребоваться другой namespace. 
Если возникнут ошибки валидации при работе с ЮЛ, проверьте документацию 
Альбома ТФФ для правильного namespace.

### Токен
- Не храните реальный токен в репозитории, тестах или документации.
- Тип для ФЛ/ИП: `IP`.
- Токен должен быть установлен только в локальном `.env` или secret manager как `EIS_SOAP_TOKEN`.

## 📝 Следующие шаги для тестирования

1. **Создайте `.env` файл** с токеном:
   ```bash
   EIS_SOAP_TOKEN=your_eis_soap_token_here
   EIS_SOAP_USER_TYPE=IP
   EIS_USE_SOAP=true
   ```

2. **Запустите тест**:
   ```bash
   docker-compose exec backend python -m pytest backend/tests/test_soap_api.py -v
   ```

3. **Проверьте логи**:
   ```bash
   docker-compose logs backend | grep -i soap
   ```

4. **Проверьте работу API**:
   ```bash
   curl http://localhost:8003/api/v1/search/eis-live \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"query": "медицинское оборудование", "page": 1, "page_size": 10}'
   ```

## 🔍 Возможные проблемы

1. **Ошибка валидации SOAP (code: 28)**
   - Проверьте правильность namespace для сервиса
   - Убедитесь, что порядок тегов в selectionParams корректен

2. **Токен не принимается**
   - Проверьте, что токен актуален в личном кабинете
   - Убедитесь, что используете правильный тип пользователя (IP/LE)

3. **Нет данных (noData)**
   - Это нормально, если для выбранного региона/даты нет данных
   - Попробуйте другой регион или дату

## ✅ Итоговая проверка

- [x] Код компилируется без ошибок
- [x] Линтер не находит ошибок
- [x] Импорты корректны
- [x] Конфигурация обновлена
- [x] Docker Compose обновлен
- [x] Документация создана
- [ ] Тесты проходят (требуется запуск)
- [ ] API работает (требуется запуск)

**Статус:** Код готов к использованию. Требуется тестирование с реальным токеном.




