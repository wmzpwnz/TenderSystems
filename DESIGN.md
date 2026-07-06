# Тендерный Хакер — Design System

Тёмный технический интерфейс для оперативного мониторинга и анализа тендеров.

## Источник Правды

- Дизайн-контракт: этот файл.
- Реальная реализация токенов и shared CSS: `/frontend/src/index.css`.
- Shared UI primitives: `/frontend/src/components/ui/`.

Если нужного цвета, шрифта, радиуса или компонента нет, сначала добавить его сюда и в shared-реализацию, потом использовать в страницах.

## Тема

Тёмная матовая UI на едином фоне `Midnight Ink`. Стиль операторский: холодная сине-серая типографика, тонкие внутренние обводки, сдержанные светящиеся акценты, blueprint-сетка на фоне. Насыщенная заливка разрешена только для одного главного действия на экране.

Формы авторизации могут использовать pill controls. Продуктовые экраны должны оставаться плотными и утилитарными.

## Цвета

| Токен | Значение | Назначение |
| --- | --- | --- |
| `--color-midnight-ink` | `#05060f` | Фон приложения и страниц |
| `--color-graphite-plate` | `#2f343e` | Карточки, модалки, панели |
| `--color-steel-border` | `#3f4959` | Поля ввода, разделители, структурные линии |
| `--color-fog` | `#81899b` | Приглушённый текст, метаданные |
| `--color-pebble` | `#9da7ba` | Второстепенный текст |
| `--color-moonlight` | `#c7d3ea` | Основной текст и иконки |
| `--color-ice` | `#d1e4fa` | Вторичные подписи, бейджи |
| `--color-glacier` | `#d8ecf8` | Заголовки, важный текст |
| `--color-frost-link` | `#b6d9fc` | Ссылки, активные акценты |
| `--color-electric-iris` | `#663af3` | Основной CTA |
| `--color-ember` | `#e46d4c` | Предупреждение/срочность |
| `--color-azure` | `#027dea` | Второстепенный синий акцент |
| `--color-cipher-mint` | `#269684` | Успех |
| `--color-blueprint-glow` | `#bacff7` | Свечение blueprint-фона |
| `--color-ember-bright` | `#ff9b83` | Ошибки, критическая срочность, active favorite |
| `--color-ember-bright-soft` | `#ffb39f` | Мягкий warning/error текст |
| `--color-premium-gold` | `#d8a14d` | Средний риск / premium-like акцент; использовать редко |

Raw hex в TSX запрещён для новых изменений. Использовать `var(--color-*)`.

## Типографика

В `index.css` сейчас заданы:

- `--font-untitled-sans`
- `--font-aeonikpro`
- `--font-dotdigital`

Но кастомные шрифты физически не подключены через `@font-face` или CDN. До отдельного решения считать рабочим стандартом fallback:

- UI/body: `Inter, ui-sans-serif, system-ui, sans-serif`
- Mono/eyebrows: `'JetBrains Mono', ui-monospace, monospace`
- Body: `14-16px`, line-height `1.43-1.5`
- Section headings: `28-48px`, line-height `1.14-1.2`
- Eyebrows: uppercase, tabular, `0.1em` tracking

Auth production typography:

| Элемент | Значение |
| --- | --- |
| Eyebrow | `18px`, uppercase, `0.24em`, mono stack |
| Title | `clamp(30px, 4vw, 40px)`, weight `500`, line-height `1.12` |
| Subtitle | `19px`, line-height `1.4` |
| Label | `17px`, weight `500` |
| Input | `18px` desktop, `16px` mobile |
| Submit | `20px` desktop, `16px` mobile |

## Форма

| Элемент | Значение |
| --- | --- |
| Product inputs/buttons | `2px` |
| Badges/chips | `6px` |
| Cards/panels | `10-16px` |
| Modals/large panels | `16px` |
| Auth cards desktop | `28px` |
| Auth cards mobile | `22px` |
| Pills/auth controls | `999px` |

## Elevation

- Без классических цветных теней.
- Использовать внутренние hairline-обводки и холодные inner glow.
- Основные токены: `--shadow-subtle`, `--shadow-subtle-4`, `--shadow-subtle-6`, `--shadow-sm`.

## Motion

- Hover/focus: `160-240ms`, `cubic-bezier(0.16, 1, 0.3, 1)`.
- Фон страницы: медленное фоновое радиальное свечение.
- Рамки секций/модалок: медленный conic glow по верхней грани.
- Обязательно уважать `prefers-reduced-motion: reduce`.

## Shared CSS Classes

- `.blueprint-page` — full-page app surface.
- `.blueprint-section` — primary page block.
- `.blueprint-panel` — nested group.
- `.blueprint-card` — repeated content card.
- `.blueprint-modal` — modal container.
- `.blueprint-input` — product input.
- `.blueprint-button-primary` — strongest action.
- `.blueprint-button-ghost` — secondary action.
- `.blueprint-pill` — pill nav/status.
- `.blueprint-status` — compact status row.
- `.blueprint-success` / `.blueprint-danger` — success/error panels.

## Auth Components

Auth pages must use React primitives from `/frontend/src/components/ui/Auth.tsx`.

Required structure:

- `AuthPage` -> `.blueprint-page.authkit-stage`
- `AuthCard` -> `.authkit-main-card`
- `AuthHeader` -> `.authkit-logo-mark`, `.authkit-eyebrow`, `.authkit-title`, `.authkit-subtitle`
- `AuthInput` -> `.authkit-label`, `.authkit-input`, `.authkit-input-icon`
- `AuthSubmit` -> `.authkit-submit`
- `AuthMessage` -> `.blueprint-success` / `.blueprint-danger`
- `AuthDivider` -> `.authkit-divider`
- `AuthTrustRow` -> `.authkit-trust-row`

Auth copy:

- Login title: `Вход в TenderSystems`
- Register title: `Регистрация в TenderSystems`

## Responsive Rules

- Проверять mobile width `375px`.
- Auth cards должны сохранять минимум `16px` horizontal viewport padding.
- При `<520px`: auth card radius `22px`, input/button height `56px`.
- Бизнес-экраны должны оставаться плотными; не превращать app shell в marketing landing.

## Правила Использования

- Новый UI сначала ищет существующий компонент/class.
- Если reusable primitive отсутствует, добавить его в `/frontend/src/components/ui/`.
- Не добавлять новые hex-цвета в TSX.
- Не использовать inline styles для статической стилизации.
- Legacy UI мигрировать постепенно при касании соответствующего экрана.
