# 🎯 TenderSystems - Система анализа госзакупок с AI

**Полнофункциональная платформа для поиска, анализа и мониторинга тендеров из Единой Информационной Системы (ЕИС) zakupki.gov.ru с интеграцией AI-анализа.**

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![React](https://img.shields.io/badge/react-18.2-blue.svg)

---

## ✨ Возможности

### 🔍 Расширенный поиск тендеров
- **15+ фильтров** - регион, ОКПД2, цена, сроки, площадка, преимущества
- **Полнотекстовый поиск** с индексами для мгновенных результатов
- **Автодополнение** в реальном времени из базы данных
- **Модальные окна** для выбора регионов (8 ФО, 83 региона) и процедур (19 типов)

### 🤖 AI-анализ тендеров
- Анализ через DeepSeek API
- Оценка конкурентоспособности
- Расчёт маржинальности
- Выявление рисков

### 📊 Интеграция с ЕИС
- **SOAP API** - официальные сервисы отдачи информации в машиночитаемом виде ✅
  - **getDocsIP** - для физических лиц (https://int.zakupki.gov.ru/eis-integration/services/getDocsIP)
  - **getDocsLE** - для юридических лиц (https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services/getDocsLE)
- **HTML парсинг** - fallback для детальной информации ✅
- ⚠️ **FTP сервер закрыт с 01.01.2025** - используется SOAP API через ЕСИА

### ⚡ Автоматизация
- **Celery Beat** - синхронизация каждый час
- **Обновление данных** каждые 6 часов
- **Очистка старых тендеров** ежедневно

---

## 💻 Требования к серверу

Перед запуском убедитесь, что ваш сервер соответствует минимальным требованиям:

- **CPU:** 2 ядра (рекомендуется 4)
- **RAM:** 4 GB (рекомендуется 8 GB)
- **Storage:** 20 GB свободного места (рекомендуется 50 GB)
- **Docker:** версия 20.10+ и Docker Compose 2.0+

📖 **[Подробные требования к серверу →](SERVER_REQUIREMENTS.md)**

---

## 🚀 Быстрый старт

### 1. Клонируйте репозиторий
\`\`\`bash
git clone https://github.com/your-username/TenderSystems.git
cd TenderSystems
\`\`\`

### 2. Создайте .env файл
\`\`\`bash
cp .env.example .env
\`\`\`

### 3. ⚠️ ВАЖНО! Заполните .env файл

**📖 [Инструкция по получению токена ЕИС →](EIS_TOKEN_SETUP.md)**

Откройте \`.env\` и замените:

\`\`\`bash
# DeepSeek API (https://platform.deepseek.com/)
DEEPSEEK_API_KEY=your_real_api_key_here

# ЕИС SOAP токены (получаются через ЕСИА в личном кабинете)
# Личный кабинет: https://zakupki.gov.ru/epz/opendata/search/results.html
# Кнопка "Получение открытых данных" над заголовком "Результаты поиска"
EIS_SOAP_TOKEN=your_token_for_individual_persons  # Токен для физических лиц (ФЛ)
EIS_SOAP_TOKEN_LE=your_token_for_legal_entities  # Токен для юридических лиц (ЮЛ, опционально)
EIS_SOAP_USER_TYPE=IP  # IP (физическое лицо) или LE (юридическое лицо)

# Секретный ключ (генерация: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your_random_32_char_secret_here

# СМЕНИТЬ ПАРОЛЬ БД!
DATABASE_URL=postgresql://tenderuser:STRONG_PASSWORD@postgres:5432/tenderdb
\`\`\`

### 4. Запустите проект
\`\`\`bash
docker-compose up -d
\`\`\`

### 5. Примените миграции
\`\`\`bash
docker-compose exec backend alembic upgrade head
\`\`\`

### 6. Откройте приложение
- **Frontend:** http://localhost:3002
- **Backend API:** http://localhost:8003
- **API Docs:** http://localhost:8003/docs

---

## 🔒 Безопасность

### ⚠️ КРИТИЧЕСКИ ВАЖНО

#### 1. Не коммитьте .env!
Проверьте:
\`\`\`bash
cat .gitignore | grep .env
\`\`\`

#### 2. Регенерируйте секреты

**SECRET_KEY:**
\`\`\`bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
\`\`\`

**Пароль БД:**
\`\`\`bash
openssl rand -base64 32
\`\`\`

#### 3. Измените дефолтные пароли

В \`docker-compose.yml\`:
\`\`\`yaml
POSTGRES_PASSWORD: \${DB_PASSWORD}
DATABASE_URL: postgresql://tenderuser:\${DB_PASSWORD}@postgres:5432/tenderdb
\`\`\`

В \`.env\`:
\`\`\`bash
DB_PASSWORD=your_strong_password_here
\`\`\`

---

## ⚙️ Переменные окружения

| Переменная | Обязательная | Описание |
|-----------|--------------|----------|
| \`DEEPSEEK_API_KEY\` | ✅ | API ключ DeepSeek |
| \`EIS_SOAP_TOKEN\` | ✅ | Токен SOAP API ЕИС для ФЛ (получается через ЕСИА) |
| \`EIS_SOAP_TOKEN_LE\` | ❌ | Токен SOAP API ЕИС для ЮЛ (если используется) |
| \`EIS_SOAP_USER_TYPE\` | ❌ | Тип пользователя: IP (ФЛ) или LE (ЮЛ), по умолчанию: IP |
| \`SECRET_KEY\` | ✅ | JWT секретный ключ |
| \`DATABASE_URL\` | ✅ | URL PostgreSQL |
| \`REDIS_URL\` | ❌ | URL Redis (по умолчанию: redis://redis:6379/0) |
| \`DEBUG\` | ❌ | Режим отладки (по умолчанию: True) |

**⚠️ ВАЖНО:** Токены ЕИС получаются в личном кабинете получателя открытых данных:
https://zakupki.gov.ru/epz/opendata/search/results.html
Кнопка "Получение открытых данных" находится над заголовком "Результаты поиска".

---

## 📚 API примеры

### Поиск тендеров
\`\`\`bash
POST /api/v1/search/advanced
{
  "query": "медицинское оборудование",
  "regions": ["77", "78"],
  "price_from": 100000,
  "platform": "roseltorg",
  "prepayment_type": "prepayment_44fz",
  "page": 1
}
\`\`\`

### Статистика
\`\`\`bash
GET /api/v1/search/filters/stats
\`\`\`

Документация: http://localhost:8003/docs

---

## 🏗 Архитектура

\`\`\`
TenderSystems/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── models/          # SQLAlchemy модели
│   │   ├── services/        # Парсеры ЕИС
│   │   └── tasks/           # Celery задачи
│   └── alembic/             # Миграции БД
├── frontend/
│   └── src/
│       ├── components/      # React компоненты
│       └── pages/           # Страницы
└── docker-compose.yml
\`\`\`

---

## 📊 Мониторинг

### Health Check
\`\`\`bash
curl http://localhost:8003/health
\`\`\`

### Логи
\`\`\`bash
docker-compose logs -f backend
docker-compose logs -f celery
\`\`\`

---

## 🔧 Разработка

### Backend
\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

### Миграции БД
\`\`\`bash
docker-compose exec backend alembic revision --autogenerate -m "Description"
docker-compose exec backend alembic upgrade head
\`\`\`

---

**Сделано с ❤️ для упрощения работы с госзакупками**


