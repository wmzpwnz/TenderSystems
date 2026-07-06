# AdvaCodex Design System

> blueprint on midnight glass

## Theme

Dark, technical, matte UI on a single Midnight Ink canvas. The interface is inspired by AuthKit's dark login-box composition, but adapted for an operational tender-monitoring product.

The system uses cool blue-gray typography, thin inset strokes, restrained luminous accents, and blueprint grid depth. Saturated fills are reserved for one dominant action per view. Auth screens may use pill-shaped controls to match the AuthKit reference; product screens stay denser and more utilitarian.

## Tokens

### Colors

| Token | Value | Usage |
| --- | --- | --- |
| `--color-midnight-ink` | `#05060f` | App canvas and page background |
| `--color-graphite-plate` | `#2f343e` | Cards, modals, panels |
| `--color-steel-border` | `#3f4959` | Inputs, dividers, structural lines |
| `--color-fog` | `#81899b` | Muted helper text and metadata |
| `--color-pebble` | `#9da7ba` | Secondary body text |
| `--color-moonlight` | `#c7d3ea` | Default body and icon color |
| `--color-ice` | `#d1e4fa` | Strong secondary labels and badges |
| `--color-glacier` | `#d8ecf8` | Headings and high-priority text |
| `--color-frost-link` | `#b6d9fc` | Links and active text accents |
| `--color-electric-iris` | `#663af3` | Primary CTA fill only |
| `--color-ember` | `#e46d4c` | Warning/urgent accent |
| `--color-azure` | `#027dea` | Low-frequency blue accent |
| `--color-cipher-mint` | `#269684` | Success accent |

### Typography

- UI/body: `--font-untitled-sans`, substitute Inter/system sans.
- Display headings: `--font-aeonikpro`, substitute system sans.
- Eyebrows/structural labels: `--font-dotdigital`, substitute JetBrains Mono/system mono.
- Body: 14-16px, line-height 1.43-1.5.
- Section headings: 28-48px, line-height 1.14-1.2.
- Eyebrows: 15px, uppercase, tabular, `0.1em` tracking.

### Shape

- Cards: `10-16px`.
- Modals/large panels: `16px`.
- Badges/chips: `6px`.
- Inputs/buttons: `2px`.
- Pills: `999px`, primarily for auth screens, chips, and status pills.

### Elevation

- Do not use traditional colored drop shadows.
- Use inset hairlines and cool inner glows:
  - `--shadow-subtle`: `rgba(186, 215, 247, 0.12) 0 0 0 1px inset`
  - `--shadow-subtle-4`: card stack with inset top line, inner glow, near-black ambient shadow
  - `--shadow-sm`: small blue glow for icon highlights

### Motion And Glow

- Motion must be quiet and functional: 160-240ms hover/focus transitions with `cubic-bezier(0.16, 1, 0.3, 1)`.
- Page canvas carries a slow ambient radial glow, not moving decorative shapes.
- Section and modal frames use a slow conic glow pulse at the top edge.
- Cards and nested panels lift by `1px` on hover and switch from hairline-only elevation to `--shadow-subtle-6`.
- Icon tiles may glow with `--shadow-sm` on hover.
- Primary buttons stay mostly flat; hover may lift by `1px`, but must not use heavy shadows.
- Respect `prefers-reduced-motion: reduce`.

## Components

### Page

Use `.blueprint-page`: full-viewport Midnight Ink background with a faint 40px blueprint grid and radial top glow.

Canvas behavior:

- Background color remains `#05060f`.
- Grid remains subtle and structural; it must not overpower the content.
- Ambient radial glow sits near the top center.
- Do not add decorative blobs, large colorful gradients, or bright image backgrounds.

### Card / Section

Use `.blueprint-section` for primary page blocks and `.blueprint-panel` for nested groups. Surfaces are matte Graphite Plate or translucent Moonlight overlays, never bright color blocks.

These surfaces include subtle animated conic/radial glow overlays. Do not add additional decorative blobs or large moving gradients.

### Buttons

Use `.blueprint-button-primary` for the single strongest action in a view. Use `.blueprint-button-ghost` for secondary actions. Buttons keep `2px` radius.

### Inputs

Use `.blueprint-input`: dark fill, Steel Border, `2px` radius, Frost Link focus ring.

### Labels

Use `.blueprint-eyebrow` for structural labels and `.blueprint-heading` for headings.

### Modals

Use `.blueprint-modal` with the same Graphite Plate surface, hairline border, and card elevation. Modal footers use translucent Midnight Ink bands.

### Auth Screens

Login and registration screens use the AuthKit-inspired composition.

#### Composition

- Root: `.blueprint-page.authkit-stage`.
- Scene wrapper: `.authkit-stack`, centered in the viewport.
- Primary form card: `.authkit-main-card`.
- Corner light points: `.authkit-card-dot` with `.authkit-dot-tl`, `.authkit-dot-tr`, `.authkit-dot-bl`, `.authkit-dot-br`.

The goal is a clean AuthKit-like login box, adapted for AdvaCodex:

- A central active login card.
- No secondary side cards or fake background forms.
- Thin glass borders, inset highlights, and a restrained blueprint canvas.
- The center card must feel smaller and sharper than a full-page modal, not like a large generic panel.

#### Auth Card

- Desktop width: about `620px`.
- Tablet/narrow width: about `540px`.
- Border radius: about `28px` desktop, `22px` mobile.
- Surface: dark translucent glass over Midnight Ink, with subtle top radial glow.
- Shadow: inner blue-gray hairlines plus deep black ambient shadow.
- Logo mark: small square glass tile, not a large hero icon.
- Title size: about `30-40px`, medium weight.
- Avoid oversized Russian headings that fill the card width.

#### Auth Controls

- Inputs use `.authkit-input`.
- Auth submit uses `.authkit-submit`.
- Auth inputs and submit are pill-shaped: `999px`.
- This is an explicit exception to the product rule where normal `.blueprint-input` and `.blueprint-button-*` keep `2px` radius.
- Auth inputs use dark translucent fill, thin cool border, and subtle inset highlight.
- Auth submit is an outline/glass control by default; do not use a large saturated purple block for the login button.
- Use `.authkit-divider` only for small structural separators such as `SECURE`, `OR`, or SSO separation.
- Use `.authkit-trust-row` for small security/status copy below the primary action.

#### Responsive Rules

- Desktop (`>=1024px`): keep one centered auth card on the blueprint canvas.
- Narrow/tablet (`<1024px`): keep the main card centered.
- Mobile (`<520px`): reduce padding, hide corner dots, keep controls at `56px` height.
- The auth card must not touch viewport edges; keep at least `16px` horizontal breathing room.

#### Auth Screen Copy

- Preferred title pattern: `Вход в AdvaCodex`, `Регистрация в AdvaCodex`.
- Subtitle should describe the immediate action, not marketing value.
- Eyebrow can be `ACCESS`, `CREATE ACCOUNT`, or another short technical label.
- Keep text concise; auth screens are not landing pages.

#### Auth Do Not

- Do not use one huge centered `.blueprint-frame` for login.
- Do not make the login title hero-sized.
- Do not use a bright filled purple login button unless the screen has another clear reason for a primary CTA.
- Do not show side ghost cards, fake forms, decorative background auth cards, or unclear UI behind the active auth card.
- Do not let global input resets override `.authkit-input` pill radius.

#### Current Production Reference

The production auth screens use:

- `.authkit-stage`
- `.authkit-stack`
- `.authkit-main-card`
- `.authkit-register-card` for registration only
- `.authkit-input`
- `.authkit-submit`

The computed production target is:

- `.authkit-input` radius: `999px`
- `.authkit-submit` radius: `999px`
- Visible ghost cards: `0`
- Login and register must share the same stage/card/control language.

## Rules

- Keep the canvas `#05060f`; do not introduce secondary page backgrounds.
- Do not use gradients as content backgrounds. The only large visual field is the blueprint grid/glow.
- Do not use saturated colors for cards, banners, or navigation states.
- Keep icons monochrome Moonlight unless signaling success/warning/error.
- Keep business screens dense and operational: no marketing hero layouts inside the app shell.
- Prefer shared blueprint utilities over raw Tailwind color utilities.
- New UI must work in dark mode only unless a light theme is explicitly requested.
- Auth screens may be visually more atmospheric than business screens, but they still follow the same Midnight Ink, glass, hairline, and restrained-glow system.
