# Тендерный Хакер (TenderSystems)

AI-платформа для поиска и анализа госзакупок РФ (44-ФЗ/223-ФЗ) из ЕИС zakupki.gov.ru: агрегация тендеров, быстрый и глубокий AI-анализ документации, оценка рисков и сметная AI-оценка для строительных закупок.

## Статус проекта

**MVP в разработке, не production-ready.** Поиск и часть интеграции с ЕИС уже работают, но AI-анализ сейчас раздвоен между старой и новой backend-системами. Это приоритет N1 перед любыми новыми AI-фичами.

## Стек

- **Backend**: FastAPI 0.104.1, SQLAlchemy 2.0.23, Alembic, PostgreSQL, Redis, Celery + Celery Beat
- **AI**: DeepSeek API через `httpx`
- **Документы**: PyPDF2, pdfplumber, python-docx, openpyxl, Pillow, pytesseract, pdf2image
- **Auth**: passlib/bcrypt, python-jose
- **Frontend**: React 18, TypeScript, Vite, Tailwind
- **Инфра**: Docker Compose, Sentry, slowapi

## Структура проекта

```text
backend/app/
  api/v1/          REST endpoints: auth, tenders, analysis, search, crm, subscriptions
  models/          SQLAlchemy models: Tender, Analysis, User, CompanyProfile
  schemas/         typed request/response schemas
  services/        EIS integration, document processing, AI analysis
  tasks/           Celery tasks
  core/            config, database, security, rate limiter, logging

frontend/src/
  pages/           route-level pages: Login, Register, Dashboard, TenderDetail, CompanyProfile
  components/      feature/shared components
  components/ui/   design-system primitives; сейчас есть auth-примитивы
```

## Запуск

Docker:

```bash
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

Локальные адреса:

- Frontend: `http://localhost:3002`
- Backend API: `http://localhost:8003`
- Swagger: `http://localhost:8003/docs`

Dev вручную:

```bash
# backend, из backend/
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# celery, из backend/
celery -A app.celery_app worker --loglevel=info
celery -A app.celery_app beat --loglevel=info

# migrations, из backend/
alembic upgrade head

# frontend, из frontend/
npm run dev
```

Перед первым запуском скопировать `.env.example` в `.env` и заполнить реальные значения. Токен ЕИС описан в `EIS_TOKEN_SETUP.md`.

## Известные проблемы

1. **Две несовместимые системы AI-анализа.** Старый путь: `analysis_service.py` + `/tenders/{id}/analyze` и `/tenders/{id}/deep-analyze`, сейчас используется `TenderDetail.tsx`. Новый путь: `deepseek_client.py` + `/analysis/*` + таблица `Analysis`, содержит нужный блок `for_construction`. Новую работу вести только через новый путь.
2. **`deepseek-chat`/`deepseek-reasoner` устаревают 24.07.2026.** В коде есть hardcode `deepseek-chat`; нужно заменить на конфигурируемую модель `deepseek-v4-flash` или `deepseek-v4-pro`.
3. **Обрезка текста документов.** В AI-анализе есть плоское ограничение текста примерно до 12-15 тыс. символов. Для крупных тендеров нужно чанкирование или предварительная суммаризация, а не молчаливая обрезка.
4. **Сметная часть пока AI-оценка.** Поля вроде `estimate_analysis`, `price_per_unit`, `win_probability` нельзя показывать как точную смету без источника расценок ФЕР/ТЕР/ГЭСН.
5. **CSRF-защита не активна.** `fastapi-csrf-protect` закомментирован в `requirements.txt`; код в `main.py` пытается подключить пакет, но при его отсутствии защита отключается.
6. **Источник ЕИС завязан на SOAP-токен.** Подходит для текущего MVP, но требует отдельного решения перед мультитенантным SaaS.
7. **UI-библиотека только начата.** В `components/ui` есть auth-примитивы; Button/Card/Input для продуктовых экранов еще нужно вынести.
8. **Production security.** Для публичного деплоя нужны `DEBUG=False`, сильный `SECRET_KEY`, корректные CORS/CSRF/secret settings.

## Дизайн

См. `DESIGN.md`. Новые UI-изменения должны использовать токены и компоненты из `frontend/src/components/ui`.

## Работа с AI-агентами

См. `AGENTS.md`. Он обязателен перед любой задачей в репозитории.
