# AGENTS.md

Прочитать перед началом любой задачи. Это обязательные правила проекта.

## Источники Правды

- Статус проекта и известные проблемы: `/README.md`
- Дизайн-токены и UI-правила: `/DESIGN.md`
- Реализация токенов/shared classes: `/frontend/src/index.css`
- Общая библиотека UI-компонентов: `/frontend/src/components/ui/`

## Как здесь работают несколько агентов одновременно

Реализацию делегируют параллельно нескольким AI-агентам: Codex — механические задачи с чёткой спецификацией (бэкенд, миграции, рефакторинг), Antigravity — фронтенд/UI с визуальной проверкой через браузерный субагент, Claude Code — исследовательские задачи. Между батчами внешний архитектор (Claude, по свежему zip-срезу) проверяет результат на дрейф/дублирование и выдаёт следующий пакет.

- Перед батчем — явная зона ответственности (файлы/директории) на каждого агента. Не выходить за неё молча.
- Следующий батч стартует только после мёржа предыдущего.
- **Документация — тоже часть зоны.** Если твоя задача не про AGENTS.md/README.md/DESIGN.md — не переписывать их куски, описывающие статус других, ещё выполняющихся в этом же батче задач: обновление статуса документации при параллельной работе — отдельная синхронная операция после мёржа всех задач батча, не часть одной из них.
- Файл общий для всех инструментов — правила действуют независимо от того, кто их читает.

## Правило №0: сначала искать, потом строить

Перед новым сервисом/компонентом/эндпоинтом — grep по названию функциональности, не существует ли уже похожая реализация. Если находятся два кандидата на одну роль — не создавать третий; выбрать один и мигрировать/удалить второй в той же задаче.

## AI-Анализ (статус: мигрировано, коммит 98cf35f)

Старая система удалена: `analysis_service.py`, `/tenders/{id}/analyze`, `/tenders/{id}/deep-analyze`, колонка `tender.deep_analysis_result` — всё удалено, включая Alembic-миграцию `006_drop_tender_deep_analysis_result`.

Единственная система сейчас: `backend/app/services/deepseek_client.py` + `/analysis/*` + таблица `Analysis` (с `user_id`, миграция `007`). `TenderDetail.tsx` использует `analysisApi.get`/`analysisApi.analyze`. Модель — конфигурируемая (`DEEPSEEK_QUICK_MODEL`/`DEEPSEEK_DEEP_MODEL`), с allowlist в коде (`deepseek-v4-flash`/`deepseek-v4-pro`), хардкода `deepseek-chat` больше нет.

Если видишь в коде обратное (упоминания `analysis_service.py`, `deep_analysis_result`) — это регрессия или чтение устаревшей копии, сообщить архитектору, не чинить молча по-старому.

## DeepSeek Model Rule

Использовать только:

- `deepseek-v4-flash`
- `deepseek-v4-pro`

Не добавлять `deepseek-chat` или `deepseek-reasoner`: эти алиасы отключаются 24.07.2026.

## Документы Тендера

Не обрезать документацию молча через `[:15000]`, `[:12000]` и похожие ограничения. Если текст не помещается в контекст:

- использовать чанкирование или суммаризацию по документам;
- логировать факт неполного покрытия;
- возвращать пользователю признак, что анализ выполнен по части документов.

## AI-Оценки

Поля вроде `estimate_analysis`, `price_per_unit`, `win_probability`, `margin_analysis` не являются фактом. В любом UI рядом с ними должна быть пометка: `AI-оценка, требует проверки`.

## Design Source Of Truth

- Новый или измененный UI должен следовать `/DESIGN.md`.
- Не добавлять новые цвета, шрифты, тени, радиусы или визуальные паттерны вне токенов.
- Не добавлять raw hex в TSX.
- Не использовать inline styles для статической стилизации.
- Если нужен reusable primitive, добавить его в `/frontend/src/components/ui/` перед использованием.
- Legacy UI мигрировать постепенно при касании экрана.

## Project Structure

- `backend/app/api/v1` — REST endpoints, thin controllers only
- `backend/app/services` — business logic, EIS clients, parsing, AI analysis
- `backend/app/models` — SQLAlchemy models
- `backend/app/schemas` — typed request/response schemas
- `backend/app/tasks` — Celery jobs
- `frontend/src/pages` — route-level pages
- `frontend/src/components` — feature/shared components
- `frontend/src/components/ui` — design-system primitives

## Backend Rules

- Keep business logic inside services.
- Keep API routes thin.
- Keep database concerns isolated in models/query code.
- Use typed schemas for external API boundaries.
- Prefer async flows where the surrounding code is async.
- Do not hardcode secrets, tokens, credentials, or environment-specific values.
- Database schema changes require Alembic migrations.

## Frontend Rules

- Pages compose components; they should not contain large business logic.
- Move reusable logic into hooks/services/components.
- Use `/DESIGN.md` tokens and established shared classes.
- Handle loading, error, empty, and success states.
- UI must be responsive at 375px mobile width and desktop.

## AI Integration Rules

- Keep prompts centralized.
- Avoid prompt duplication.
- Separate orchestration from providers.
- Separate memory/storage from generation.
- Keep AI integrations modular and configurable.

## Commit Rules

- When committing: one commit = one page, feature, or isolated fix.
- Do not bundle unrelated changes.
- Commit message format: `feat(scope): short description`, `fix(scope): short description`, `refactor(scope): short description`, or `chore(scope): short description`.

## Definition Of Done

For any changed page or user-facing flow:

- [ ] Uses `/DESIGN.md` tokens and shared UI patterns
- [ ] Handles loading / error / empty states
- [ ] Responsive at 375px and desktop
- [ ] No browser console errors caused by the change
- [ ] Backend/API changes have focused tests where practical
- [ ] No dead code, console spam, placeholder logic, or temporary hacks
- [ ] Relevant build/test command was run or explicitly reported as not run

For analysis features:

- [ ] Uses `deepseek_client.py` and `analysisApi`, not `analysis_service.py`
- [ ] Model is `deepseek-v4-flash` or `deepseek-v4-pro`
- [ ] AI estimates are marked as requiring verification
- [ ] Document truncation is logged/reported, not silent

## Commands

### Full Stack

```bash
docker-compose up -d
```

### Backend

```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm run dev
```

### Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Backend Tests

```bash
docker-compose exec backend python -m pytest tests -v
```

### Frontend Build

```bash
cd frontend
npm run build
```

### System Check

```bash
./test_system.sh
```
