# Design Overhaul Plan — "Limpid v2"

## Diagnosis: What feels "AI-built" today

The current design is _functional_ but reads as a generic Tailwind template:

- **Typography**: System font stack only. No typographic personality. Every heading is just `font-bold` in varying sizes. No letter-spacing, no optical weight adjustments. Text all looks the same.
- **Color**: The indigo palette is Tailwind's stock `indigo-*`. No custom tuning. The `bg-base: #f8fafc` is `slate-50` verbatim. No warmth, no character.
- **Spacing**: Uniform `py-8`, `gap-6`, `space-y-2` everywhere. No rhythm, no breathing room, no intentional density shifts.
- **Cards**: Plain white box + 1px border + `shadow-sm`. Every card is identical. No hierarchy between primary and secondary content.
- **Buttons**: Stock rounded-lg + bg-primary-600. No hover animations, no depth, no personality.
- **Nav**: Standard sidebar list. No logo mark, no visual weight, no spatial separation between groups.
- **Transitions**: Zero. No page entrance, no hover feedback beyond color change, no HTMX swap animation. The app feels static and lifeless.
- **Details**: No decorative elements. No subtle textures. No border refinements. No personality anywhere.

## Design direction: "Quiet precision"

A financial tool that feels _crafted_, not _generated_. Think: Stripe dashboard meets Notion's calm. Precise typography, deliberate spacing, understated motion that signals quality.

**Principles:**
1. **Typographic hierarchy is the design** — Use a proper type scale with a distinctive font pairing
2. **Depth through light, not shadow** — Subtle background tints and border treatments instead of drop shadows
3. **Motion as feedback** — Every interaction gets a response: hovers lift, swaps fade, badges pulse
4. **Density with purpose** — Financial data is dense; embrace it with a tighter grid and clear visual lanes
5. **One accent, used sparingly** — The primary color should feel like a highlight pen, not a paint bucket

---

## 1. Typography

### Font pairing

Load **Inter** as body (yes, despite being common — it has the best tabular figures for financial data) with **tight tracking on headings** to differentiate. Use a heavier weight range (450 for body, 650 for semibold) via variable font for subtle distinction from default 400/600.

Alternative worth considering: **Geist** (by Vercel) — designed for dashboards, has excellent monospace variant for numbers.

**Recommended: Geist + Geist Mono**
- Geist: clean, modern, designed for interfaces — not overused yet
- Geist Mono: perfect for financial numbers (tabular figures built-in)

### Implementation

```html
<!-- base.html <head> -->
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1.3.1/dist/fonts/geist-sans/style.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1.3.1/dist/fonts/geist-mono/style.min.css">
```

### Type scale (in main.css)

```css
@theme {
  --font-sans: 'Geist', system-ui, -apple-system, sans-serif;
  --font-mono: 'Geist Mono', ui-monospace, monospace;
}

@layer base {
  body {
    font-family: var(--font-sans);
    font-size: 0.9375rem; /* 15px */
    line-height: 1.6;
    font-weight: 400;
    color: var(--color-text);
    background-color: var(--color-bg-base);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  h1, h2, h3, h4 {
    letter-spacing: -0.025em;
    font-weight: 600;
  }

  /* Tabular numbers for financial data */
  .font-mono, [data-value], td:last-child {
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
  }
}
```

### Heading classes

Replace generic `text-2xl font-bold` with intentional heading styles:

```html
<!-- Page title (h1) — used once per page -->
<h1 class="text-[1.75rem] font-semibold tracking-tight text-text">

<!-- Section title (h2) -->
<h2 class="text-lg font-semibold tracking-tight text-text">

<!-- Card title (h3) -->
<h3 class="text-[0.8125rem] font-medium uppercase tracking-wide text-text-muted">
```

The card title change is significant: switching from large bold text to **small uppercase tracking-wide** gives a "label" feel that's more sophisticated. The content inside the card speaks for itself.

---

## 2. Color palette

Replace stock Tailwind indigo with a custom-tuned palette. Warmer, less saturated, more refined.

```css
@theme {
  /* Primary: custom indigo — slightly warmer, less electric */
  --color-primary-50: #f0f0ff;
  --color-primary-100: #e0e1ff;
  --color-primary-200: #c4c5fe;
  --color-primary-300: #a3a4fc;
  --color-primary-400: #8182f7;
  --color-primary-500: #6364ed;
  --color-primary-600: #4e4ddb;  /* main action */
  --color-primary-700: #4240ba;
  --color-primary-800: #373596;
  --color-primary-900: #2e2c78;

  /* Backgrounds — warm, not clinical */
  --color-bg-base: #fafaf9;     /* stone-50 — warmer than slate */
  --color-bg-card: #ffffff;
  --color-bg-elevated: #ffffff;
  --color-bg-subtle: #f5f5f4;   /* stone-100 — for inset sections */
  --color-bg-hover: #f5f5f4;

  /* Text — slightly warmer than pure slate */
  --color-text: #1c1917;        /* stone-900 */
  --color-text-muted: #78716c;  /* stone-500 */
  --color-text-faint: #a8a29e;  /* stone-400 — for timestamps, annotations */

  /* Border — refined */
  --color-border: #e7e5e4;      /* stone-200 */
  --color-border-strong: #d6d3d1; /* stone-300 — for cards, dividers */

  /* Semantic: keep as-is but add 400 stops for hover states */
  --color-success-400: #4ade80;
  --color-warning-400: #fbbf24;
  --color-danger-400: #f87171;
}
```

Key changes:
- Move from `slate` (cold blue-gray) to `stone` (warm neutral). Finance should feel warm and approachable, not clinical.
- Custom-tuned primary that's less electric/neon than stock indigo
- Add `text-faint` for tertiary text (timestamps, annotations, metadata)
- Add `bg-subtle` for inset content areas (form backgrounds, nested sections)
- Add `border-strong` for elements that need more definition

---

## 3. Card system overhaul

The card is the most used component. It needs hierarchy.

### New card_start.html

```html
{% load i18n %}
<div class="rounded-2xl border bg-bg-card
  {% if variant == 'warning' %}border-warning-400/40{% elif variant == 'success' %}border-success-400/40{% elif variant == 'elevated' %}border-border shadow-md shadow-black/[0.03]{% else %}border-border{% endif %}
  {% if flush %}{% else %}p-5 sm:p-6{% endif %}">
  {% if title %}
  <div class="{% if flush %}px-5 pt-5 sm:px-6 sm:pt-6{% endif %} mb-4">
    <h3 class="text-[0.8125rem] font-medium uppercase tracking-wide text-text-muted">
      {% if icon %}<span class="mr-1.5 inline-block align-middle">{{ icon }}</span>{% endif %}
      {{ title }}
    </h3>
  </div>
  {% endif %}
  <div class="{% if flush %}px-5 pb-5 sm:px-6 sm:pb-6{% endif %}">
```

### Variant: stat card (for big numbers)

A new card type for hero metrics (property value, total equity, etc.):

```html
<!-- components/stat_card.html -->
{% load i18n %}
<div class="rounded-2xl border border-border bg-bg-card p-5 sm:p-6">
  <p class="text-[0.8125rem] font-medium uppercase tracking-wide text-text-muted">{{ label }}</p>
  <p class="mt-2 text-[1.75rem] font-semibold tracking-tight text-text font-mono">{{ value }}</p>
  {% if annotation %}
  <p class="mt-1 text-sm text-text-faint">{{ annotation }}</p>
  {% endif %}
</div>
```

### Usage example — property detail hero

```html
<!-- Before: generic card with card_start/card_end -->
<!-- After: stat cards in a tight grid -->
<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
  {% include "components/stat_card.html" with label=_("Value") value=snapshot.current_valuation|cad %}
  {% include "components/stat_card.html" with label=_("Equity") value=snapshot.equity|cad annotation=snapshot.equity_pct|floatformat:1|add:"%" %}
  {% include "components/stat_card.html" with label=_("Mortgage") value=snapshot.mortgage_balance|cad %}
  {% include "components/stat_card.html" with label=_("Your share") value=owner_snapshot.your_equity|cad annotation=owner_snapshot.share_pct|floatformat:0|add:"%" %}
</div>
```

This replaces the current 2-column card layout with metric_rows inside. Much denser, more scannable, more modern.

---

## 4. Navigation redesign

### Sidebar — Desktop

The sidebar should feel anchored and calm, with clear grouping.

```html
<aside class="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r border-border bg-bg-card md:flex">
  <!-- Logo: wordmark with subtle weight -->
  <div class="flex h-14 items-center px-5">
    <a href="{% url 'home' %}" class="flex items-center gap-2">
      <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-600">
        <span class="text-sm font-bold text-white">L</span>
      </div>
      <span class="text-base font-semibold tracking-tight text-text">Limpid</span>
    </a>
  </div>

  <nav class="flex-1 space-y-0.5 px-3 py-3" aria-label="{% trans 'Main navigation' %}">
    <!-- Active state: left accent bar instead of background fill -->
    <a href="..." class="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium
      {% if active %}text-primary-700{% else %}text-text-muted hover:text-text hover:bg-bg-hover{% endif %}
      transition-colors duration-150">
      {% if active %}
      <span class="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full bg-primary-600"></span>
      {% endif %}
      <svg class="h-[18px] w-[18px] shrink-0 {% if active %}text-primary-600{% else %}text-text-faint group-hover:text-text-muted{% endif %} transition-colors" ...></svg>
      Label
    </a>

    <!-- Section separator -->
    <div class="my-3 border-t border-border"></div>

    <!-- Notifications with badge -->
    ...
  </nav>

  <!-- User section at bottom -->
  <div class="border-t border-border px-3 py-3">
    <div class="flex items-center gap-3 rounded-lg px-3 py-2">
      <div class="flex h-8 w-8 items-center justify-center rounded-full bg-bg-subtle text-sm font-medium text-text-muted">
        {{ user.first_name.0 }}{{ user.last_name.0 }}
      </div>
      <div class="flex-1 min-w-0">
        <p class="truncate text-sm font-medium text-text">{{ user.get_full_name }}</p>
      </div>
    </div>
  </div>
</aside>
```

Key changes:
- **Logo mark**: Small colored square with "L" + wordmark. Gives a brand anchor.
- **Active indicator**: Left accent bar (3px) instead of background fill. More subtle, more modern.
- **Icon sizing**: 18px instead of 20px. Tighter proportions.
- **User avatar**: Initials circle instead of icon. Personal, distinctive.
- **Section dividers**: Thin borders to group related nav items (Main, Finance, Settings).

### Bottom nav — Mobile

```html
<nav class="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-bg-card/95 backdrop-blur-lg md:hidden safe-area-bottom">
  <div class="flex items-center justify-around py-1.5">
    <a href="..." class="flex flex-col items-center gap-0.5 px-3 py-1.5 text-[0.625rem] font-medium
      {% if active %}text-primary-600{% else %}text-text-muted{% endif %}
      transition-colors duration-150">
      <!-- Active dot above icon instead of color-only -->
      {% if active %}<span class="mb-0.5 h-1 w-1 rounded-full bg-primary-500"></span>{% endif %}
      <svg class="h-5 w-5" ...></svg>
      Label
    </a>
  </div>
</nav>
```

Key changes:
- `backdrop-blur-lg` + semi-transparent background: content scrolls behind the nav, glass effect
- Active dot indicator above the icon
- `safe-area-bottom` utility for iPhone notch
- Tighter vertical padding

```css
@utility safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
```

---

## 5. Motion & transitions

### Global transitions (main.css)

```css
@layer base {
  /* Smooth color transitions on interactive elements */
  a, button, input, select, textarea {
    transition: color 150ms ease, background-color 150ms ease,
                border-color 150ms ease, box-shadow 150ms ease;
  }

  /* Fade-in for HTMX swapped content */
  .htmx-added {
    animation: fadeIn 200ms ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* Subtle slide for HTMX settling */
  .htmx-settling {
    opacity: 0;
  }

  /* Page entrance — staggered children */
  .animate-enter > * {
    animation: fadeSlideUp 300ms ease-out both;
  }
  .animate-enter > *:nth-child(1) { animation-delay: 0ms; }
  .animate-enter > *:nth-child(2) { animation-delay: 50ms; }
  .animate-enter > *:nth-child(3) { animation-delay: 100ms; }
  .animate-enter > *:nth-child(4) { animation-delay: 150ms; }
  .animate-enter > *:nth-child(5) { animation-delay: 200ms; }
  .animate-enter > *:nth-child(6) { animation-delay: 250ms; }

  @keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
}
```

### Button hover lift

```css
@layer components {
  .btn-primary {
    @apply rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-medium text-white;
    transition: all 150ms ease;
  }
  .btn-primary:hover {
    @apply bg-primary-700;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px -2px rgb(78 77 219 / 0.3);
  }
  .btn-primary:active {
    transform: translateY(0);
    box-shadow: none;
  }
}
```

### Card hover (for clickable cards like property list)

```css
@layer components {
  .card-interactive {
    transition: all 200ms ease;
  }
  .card-interactive:hover {
    border-color: var(--color-border-strong);
    box-shadow: 0 4px 16px -4px rgb(0 0 0 / 0.06);
    transform: translateY(-2px);
  }
}
```

### Notification badge pulse

```css
@layer components {
  .badge-notification {
    animation: pulse-subtle 2s ease-in-out infinite;
  }
  @keyframes pulse-subtle {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }
}
```

### Toast messages auto-dismiss

```html
<!-- base.html messages -->
{% for message in messages %}
<div class="rounded-xl border px-4 py-3 text-sm animate-toast-in"
     x-data="{ show: true }"
     x-show="show"
     x-init="setTimeout(() => show = false, 5000)"
     x-transition:leave="transition ease-in duration-200"
     x-transition:leave-start="opacity-100 translate-y-0"
     x-transition:leave-end="opacity-0 -translate-y-2"
     ...>
```

```css
@keyframes toastIn {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-toast-in {
  animation: toastIn 300ms ease-out;
}
```

---

## 6. Component refinements

### Badge — softer, more refined

```html
<!-- components/badge.html -->
{% if variant == 'success' %}
<span class="inline-flex items-center rounded-md bg-success-50 px-2 py-0.5 text-xs font-medium text-success-700 ring-1 ring-inset ring-success-500/20">{{ label }}</span>
{% elif variant == 'warning' %}
<span class="inline-flex items-center rounded-md bg-warning-50 px-2 py-0.5 text-xs font-medium text-warning-700 ring-1 ring-inset ring-warning-500/20">{{ label }}</span>
{% elif variant == 'danger' %}
<span class="inline-flex items-center rounded-md bg-danger-50 px-2 py-0.5 text-xs font-medium text-danger-700 ring-1 ring-inset ring-danger-500/20">{{ label }}</span>
{% elif variant == 'neutral' %}
<span class="inline-flex items-center rounded-md bg-bg-subtle px-2 py-0.5 text-xs font-medium text-text-muted ring-1 ring-inset ring-border">{{ label }}</span>
{% else %}
<span class="inline-flex items-center rounded-md bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700 ring-1 ring-inset ring-primary-500/20">{{ label }}</span>
{% endif %}
```

Changes: `rounded-full` → `rounded-md` (less playful, more precise), add `ring-1 ring-inset` for subtle border definition.

### Metric row — cleaner alignment

```html
<!-- components/metric_row.html -->
<div class="flex items-baseline justify-between py-2.5 border-b border-border/60 last:border-0">
  <dt class="text-sm text-text-muted">{{ label }}</dt>
  <dd class="text-sm font-medium text-text font-mono tabular-nums">
    {{ value }}
    {% if annotation %}<span class="ml-1.5 text-xs text-text-faint">({{ annotation }})</span>{% endif %}
  </dd>
</div>
```

Changes: Add `border-b` between rows for visual lanes (financial data readability). Use `font-mono tabular-nums` for number alignment.

### Tooltip — cleaner popover

```html
<!-- components/tooltip.html -->
<span class="relative inline-block" x-data="{ open: false }">
  <button type="button"
          @click="open = !open"
          @click.outside="open = false"
          class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-medium text-text-faint hover:text-text-muted hover:bg-bg-subtle transition-colors"
          aria-describedby="tooltip-{{ id }}">
    ?
  </button>
  <!-- Desktop popover -->
  <div x-show="open"
       x-transition:enter="transition ease-out duration-150"
       x-transition:enter-start="opacity-0 translate-y-1"
       x-transition:enter-end="opacity-1 translate-y-0"
       x-transition:leave="transition ease-in duration-100"
       x-transition:leave-start="opacity-100"
       x-transition:leave-end="opacity-0"
       class="absolute bottom-full left-1/2 z-40 mb-2 hidden w-64 -translate-x-1/2 rounded-xl border border-border bg-bg-card p-4 text-sm text-text shadow-lg ring-1 ring-black/5 md:block">
    {{ text }}
  </div>
  <!-- Mobile bottom sheet -->
  ...
</span>
```

Changes: Entry/exit transitions on the popover. `ring-1 ring-black/5` for depth. Larger padding.

### Form inputs — unified style

```css
@layer components {
  .input {
    @apply w-full rounded-xl border border-border bg-bg-card px-3.5 py-2.5 text-sm text-text
           placeholder:text-text-faint
           focus:border-primary-400 focus:ring-2 focus:ring-primary-100 focus:outline-none
           transition-all duration-150;
  }
  .input-error {
    @apply border-danger-400 focus:border-danger-400 focus:ring-danger-100;
  }
}
```

### Progress bar — smoother

```html
<div class="h-1.5 w-full overflow-hidden rounded-full bg-bg-subtle">
  <div class="h-full rounded-full bg-primary-500 transition-all duration-500 ease-out"
       style="width: {% widthratio current total 100 %}%"></div>
</div>
```

Changes: Thinner (1.5 instead of 2), smoother transition for animated updates, remove text above.

---

## 7. Page-level layout improvements

### Property detail — dense data layout

The current detail page stacks cards vertically. A more refined approach:

```html
{% block content %}
<div class="animate-enter space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-[1.75rem] font-semibold tracking-tight text-text">{{ property.name }}</h1>
      <p class="mt-1 text-sm text-text-muted">{{ property.address }}, {{ property.city }}</p>
    </div>
    <div class="flex items-center gap-2">
      {% include "components/badge.html" with label=property.get_usage_display variant="neutral" %}
      {% if ownership.is_admin %}
      <a href="{% url 'real_estate:edit' property.pk %}" class="btn-ghost">{% trans "Edit" %}</a>
      {% endif %}
    </div>
  </div>

  <!-- Stat cards row -->
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    {% include "components/stat_card.html" ... %}
  </div>

  <!-- 2-column content -->
  <div class="grid gap-6 lg:grid-cols-3">
    <div class="lg:col-span-2 space-y-6">
      <!-- Charts, expenses, valuations -->
    </div>
    <div class="space-y-6">
      <!-- Ownership, mortgage, taxes (sidebar info) -->
    </div>
  </div>
</div>
{% endblock %}
```

### Home page — refined hero

```html
<div class="py-16 text-center md:py-24 animate-enter">
  <div class="mx-auto max-w-2xl">
    <h1 class="text-[2.5rem] font-semibold tracking-tight text-text sm:text-5xl md:text-[3.5rem] leading-[1.1]">
      {% trans "Understand before you invest" %}
    </h1>
    <p class="mx-auto mt-6 max-w-lg text-base text-text-muted leading-relaxed">
      {% trans "Radical transparency and a progressive learning path — so you always know what you hold, what it costs, and what you need to learn." %}
    </p>
    <div class="mt-10 flex items-center justify-center gap-4">
      <a href="..." class="btn-primary">{% trans "Get started" %}</a>
      <a href="..." class="text-sm font-medium text-text-muted hover:text-text transition-colors">
        {% trans "Start learning" %} <span class="ml-1">&rarr;</span>
      </a>
    </div>
  </div>
</div>
```

Changes: Tighter line-height on hero (1.1), larger size range, more vertical breathing room.

---

## 8. Empty states

Currently just "No properties yet." in a plain card. Add personality:

```html
<!-- components/empty_state.html -->
<div class="flex flex-col items-center py-16 text-center">
  <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-bg-subtle text-text-faint">
    {{ icon|safe }}
  </div>
  <h3 class="mt-4 text-sm font-semibold text-text">{{ title }}</h3>
  <p class="mt-1 max-w-sm text-sm text-text-muted">{{ description }}</p>
  {% if action_url %}
  <a href="{{ action_url }}" class="btn-primary mt-6">{{ action_label }}</a>
  {% endif %}
</div>
```

---

## 9. Login/signup — distinctive auth page

Auth pages should feel special, not like regular content pages:

```html
{% block content %}
<div class="flex min-h-[80vh] items-center justify-center">
  <div class="w-full max-w-sm">
    <!-- Logo centered -->
    <div class="mb-8 flex justify-center">
      <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary-600">
        <span class="text-lg font-bold text-white">L</span>
      </div>
    </div>
    <h1 class="text-center text-xl font-semibold tracking-tight text-text">{% trans "Welcome back" %}</h1>
    <p class="mt-1 text-center text-sm text-text-muted">{% trans "Sign in to your account" %}</p>

    <form class="mt-8 space-y-4">
      ...
    </form>
  </div>
</div>
{% endblock %}
```

No card wrapper. Floating form in the center of the page. Logo mark above.

---

## 10. Disclaimer banner — less intrusive

```html
<div class="border-b border-warning-200/60 bg-warning-50/50 px-4 py-1.5 text-center text-xs text-warning-700"
     x-data="{ show: true }" x-show="show"
     x-transition:leave="transition ease-in duration-150"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0">
  {% trans "Educational tool — not financial advice." %}
  <button @click="show = false" class="ml-2 text-warning-600 hover:text-warning-800 transition-colors">&times;</button>
</div>
```

Shorter, less alarming, dismiss with &times; icon.

---

## Implementation order

### Phase 1 — Foundation (CSS only, no template changes)
1. Add Geist font loading to `base.html`
2. Rewrite `main.css` with new theme tokens, type scale, base styles, and transitions
3. Add utility classes: `safe-area-bottom`, HTMX animations, button/input components
4. **Result**: Everything immediately looks different without touching a single template

### Phase 2 — Core components
5. Update `card_start.html` / `card_end.html` — new padding, rounded-2xl, uppercase title
6. Create `stat_card.html`
7. Update `badge.html` — rounded-md + ring
8. Update `metric_row.html` — border-b lanes, font-mono
9. Update `tooltip.html` — transitions
10. Update `progress_bar.html` — thinner
11. Create `empty_state.html`
12. Add `btn-primary`, `btn-ghost`, `input` component classes

### Phase 3 — Navigation
13. Redesign `nav.html` — logo mark, left accent bar, initials avatar, section dividers
14. Redesign `bottom_nav.html` — backdrop-blur, dot indicator, safe area
15. Update `disclaimer_banner.html`

### Phase 4 — Pages
16. Rework `home.html` — hero with animate-enter
17. Rework `login.html` / `signup.html` — centered floating form
18. Rework `real_estate/detail.html` — stat cards + 3-column layout
19. Rework `real_estate/list.html` — interactive card hover
20. Rework `notifications.html` — refine spacing
21. Update `footer.html`

### Phase 5 — Polish
22. Add `animate-enter` to all page content blocks
23. HTMX swap animations (fadeIn on htmx-added)
24. Toast messages auto-dismiss
25. Review all pages for consistent use of new tokens

---

## Files changed

| File | Change |
|------|--------|
| `base.html` | Geist fonts, message animation |
| `frontend/src/styles/main.css` | Full rewrite — theme, base, components, animations |
| `templates/components/card_start.html` | Rounded-2xl, uppercase title |
| `templates/components/card_end.html` | No change |
| `templates/components/badge.html` | Rounded-md, ring |
| `templates/components/metric_row.html` | Border-b, font-mono |
| `templates/components/tooltip.html` | Transitions |
| `templates/components/progress_bar.html` | Thinner |
| `templates/components/nav.html` | Full redesign |
| `templates/components/bottom_nav.html` | Backdrop blur, dot |
| `templates/components/disclaimer_banner.html` | Shorter |
| `templates/components/footer.html` | Minor spacing |
| `templates/components/stat_card.html` | **New** |
| `templates/components/empty_state.html` | **New** |
| `templates/pages/home.html` | Hero redesign |
| `templates/account/login.html` | Centered floating |
| `templates/account/signup.html` | Centered floating |
| `templates/real_estate/list.html` | Card hover |
| `templates/real_estate/detail.html` | Stat cards, 3-col |
| `templates/real_estate/notifications.html` | Spacing |

No backend/Python changes required. All changes are CSS + templates.

---

## Detailed TODO list

### Phase 1 — Foundation (CSS + base.html only)

The goal is to change the _feel_ of the entire app by touching only 2 files. No template logic changes — just theme tokens, base styles, and font loading. After this phase, every page already looks noticeably different.

- [x] **1.1 — Load Geist fonts in `base.html`**
  - Add `<link rel="preconnect">` and two `<link rel="stylesheet">` tags for Geist Sans and Geist Mono from jsDelivr CDN
  - Place them before `{% vite_hmr_client %}` so fonts start loading early
  - File: `templates/base.html`

- [x] **1.2 — Rewrite `@theme` block in `main.css`**
  - Replace stock indigo palette with custom-tuned warmer indigo (see Section 2)
  - Replace `bg-base` (#f8fafc slate-50) with #fafaf9 (stone-50)
  - Replace `text` (#1e293b slate-800) with #1c1917 (stone-900)
  - Replace `text-muted` (#64748b slate-500) with #78716c (stone-500)
  - Replace `border` (#e2e8f0 slate-200) with #e7e5e4 (stone-200)
  - Add new tokens: `--color-text-faint`, `--color-bg-subtle`, `--color-bg-hover`, `--color-bg-elevated`, `--color-border-strong`
  - Add new semantic 400 stops: `--color-success-400`, `--color-warning-400`, `--color-danger-400`
  - Add font family tokens: `--font-sans: 'Geist'`, `--font-mono: 'Geist Mono'`
  - File: `frontend/src/styles/main.css`

- [x] **1.3 — Rewrite `@layer base` in `main.css`**
  - Set `font-family: var(--font-sans)` on body
  - Add `-webkit-font-smoothing: antialiased` and `-moz-osx-font-smoothing: grayscale`
  - Add heading rules: `h1, h2, h3, h4 { letter-spacing: -0.025em; font-weight: 600; }`
  - Add tabular-nums rule for `.font-mono` and `td:last-child`
  - Add global interactive transition: `a, button, input, select, textarea { transition: color 150ms, background-color 150ms, border-color 150ms, box-shadow 150ms; }`
  - File: `frontend/src/styles/main.css`

- [x] **1.4 — Add HTMX animation classes in `main.css`**
  - Add `.htmx-added` fade-in animation (opacity 0→1, translateY 4px→0, 200ms)
  - Add `.htmx-settling { opacity: 0; }` for swap-out
  - File: `frontend/src/styles/main.css`

- [x] **1.5 — Add `animate-enter` staggered entrance in `main.css`**
  - Define `@keyframes fadeSlideUp` (opacity 0→1, translateY 8px→0)
  - `.animate-enter > *` with 300ms duration
  - Stagger with `nth-child(1)` through `nth-child(6)` at 50ms intervals
  - File: `frontend/src/styles/main.css`

- [x] **1.6 — Add component classes in `main.css`**
  - `.btn-primary` — rounded-xl, bg-primary-600, hover lift (translateY -1px) + colored shadow, active press
  - `.btn-ghost` — transparent bg, text-text-muted, hover bg-bg-hover, rounded-lg
  - `.btn-danger` — rounded-xl, bg-danger-600, hover lift + red shadow
  - `.input` — rounded-xl, border-border, focus ring primary-100, placeholder text-faint
  - `.input-error` — border-danger-400 variant
  - `.card-interactive` — hover translateY(-2px), border-strong, subtle shadow
  - `.badge-notification` — pulse-subtle animation (opacity 1→0.7→1, 2s loop)
  - `.animate-toast-in` — translateY(-8px)→0, opacity 0→1, 300ms
  - File: `frontend/src/styles/main.css`

- [x] **1.7 — Add `safe-area-bottom` utility in `main.css`**
  - `@utility safe-area-bottom { padding-bottom: env(safe-area-inset-bottom, 0px); }`
  - File: `frontend/src/styles/main.css`

- [x] **1.8 — Visual check: run dev server and verify**
  - `uv run python manage.py runserver` + `npm run dev` in `frontend/`
  - Check home, login, real estate list, real estate detail
  - Verify Geist fonts load (check Network tab)
  - Verify warm color shift is visible (backgrounds, text, borders)
  - Verify no broken styles from token renames

---

### Phase 2 — Core components

Update the shared component partials to match the new design language. These changes cascade to every page that uses them.

- [x] **2.1 — Update `card_start.html`**
  - Change `rounded-xl` → `rounded-2xl`
  - Remove `shadow-sm`
  - Change title from `<h3 class="text-base font-semibold text-text">` to `<h3 class="text-[0.8125rem] font-medium uppercase tracking-wide text-text-muted">`
  - Remove border-b from title area, replace with `mb-4` spacing
  - Change padding from `px-5 py-4` to `p-5 sm:p-6`
  - Add `elevated` variant with `shadow-md shadow-black/[0.03]`
  - File: `templates/components/card_start.html`

- [x] **2.2 — Create `stat_card.html`**
  - New component: rounded-2xl card with uppercase label, large mono number, optional annotation
  - Label: `text-[0.8125rem] font-medium uppercase tracking-wide text-text-muted`
  - Value: `text-[1.75rem] font-semibold tracking-tight text-text font-mono`
  - Annotation: `text-sm text-text-faint`
  - File: `templates/components/stat_card.html` (new)

- [x] **2.3 — Update `badge.html`**
  - Change `rounded-full` → `rounded-md`
  - Add `ring-1 ring-inset ring-{color}-500/20` to each variant
  - Change neutral variant to use `bg-bg-subtle` + `ring-border` instead of `bg-gray-100`
  - File: `templates/components/badge.html`

- [x] **2.4 — Update `metric_row.html`**
  - Add `border-b border-border/60 last:border-0` for visual lanes
  - Change padding from `py-2` to `py-2.5`
  - Add `font-mono tabular-nums` to `<dd>` value
  - Change annotation color from `text-text-muted` to `text-text-faint`
  - File: `templates/components/metric_row.html`

- [x] **2.5 — Update `tooltip.html`**
  - Add Alpine `x-transition` directives to desktop popover (enter/leave, 150ms/100ms)
  - Change popover `rounded-lg` → `rounded-xl`
  - Add `ring-1 ring-black/5` for depth
  - Change padding from `p-3` to `p-4`
  - Change trigger button: remove `bg-gray-200`, use `text-text-faint hover:text-text-muted hover:bg-bg-subtle`
  - Add Alpine transitions to mobile bottom sheet too
  - File: `templates/components/tooltip.html`

- [x] **2.6 — Update `progress_bar.html`**
  - Change bar height from `h-2` to `h-1.5`
  - Change track color from `bg-gray-200` to `bg-bg-subtle`
  - Change fill color from `bg-primary-600` to `bg-primary-500`
  - Add `transition-all duration-500 ease-out` to fill
  - Remove "Step X of Y" text above (or keep it but style as `text-xs text-text-faint`)
  - File: `templates/components/progress_bar.html`

- [x] **2.7 — Create `empty_state.html`**
  - New component: centered icon (in rounded-2xl bg-subtle container), title, description, optional CTA
  - Accept props: `icon` (safe HTML), `title`, `description`, `action_url`, `action_label`
  - File: `templates/components/empty_state.html` (new)

- [x] **2.8 — Update `callout_start.html`**
  - Change `rounded-lg` → `rounded-xl`
  - Adjust border-l-4 width to `border-l-[3px]` for refinement
  - Use new `text-text-faint` for secondary callout text if applicable
  - File: `templates/components/callout_start.html`

- [x] **2.9 — Visual check: component review**
  - Navigate to real estate detail page (uses card, metric_row, badge heavily)
  - Verify uppercase card titles look correct
  - Verify metric rows have separator lines
  - Verify badges use rounded-md + ring
  - Check tooltip popover transitions work

---

### Phase 3 — Navigation

Redesign the sidebar and bottom nav. These are on every page, so they define the whole feel.

- [x] **3.1 — Redesign `nav.html` (desktop sidebar)**
  - Replace text-only logo with logo mark (rounded-lg bg-primary-600 square with "L") + wordmark
  - Change sidebar width from `w-60` to `w-56`
  - Replace active state from `bg-primary-50 text-primary-700` to left accent bar (`absolute left-0, h-5, w-[3px], rounded-full, bg-primary-600`) + `text-primary-700`
  - Add `transition-colors duration-150` to all nav links
  - Change icon size from `h-5 w-5` to `h-[18px] w-[18px]`
  - Change inactive icon color from `text-text-muted` to `text-text-faint` with `group-hover:text-text-muted`
  - Add hover state: `hover:bg-bg-hover hover:text-text`
  - Add section dividers (`<div class="my-3 border-t border-border">`) between nav groups:
    - Group 1: Home, Dashboard
    - Group 2: Portfolios, Learn, Scenarios, Real Estate, Impact
    - Group 3: Notifications
  - Replace bottom profile section: user icon → initials circle (`h-8 w-8 rounded-full bg-bg-subtle`) with `{{ user.first_name.0 }}{{ user.last_name.0 }}`
  - Show user full name as truncated text next to initials
  - Keep logout link but style as ghost
  - Update `md:pl-60` in `base.html` to `md:pl-56` to match new sidebar width
  - Files: `templates/components/nav.html`, `templates/base.html`

- [x] **3.2 — Redesign `bottom_nav.html` (mobile)**
  - Add `bg-bg-card/95 backdrop-blur-lg` for glass effect
  - Add `safe-area-bottom` class (from Phase 1.7)
  - Add active dot indicator: `<span class="mb-0.5 h-1 w-1 rounded-full bg-primary-500">` above icon when active
  - Change label size from `text-xs` to `text-[0.625rem]`
  - Change vertical padding from `py-2` to `py-1.5`
  - Add `transition-colors duration-150` to all nav links
  - Use `badge-notification` class on notification count badge
  - File: `templates/components/bottom_nav.html`

- [x] **3.3 — Update `disclaimer_banner.html`**
  - Shorten text to "Educational tool — not financial advice."
  - Change background from `bg-amber-50` to `bg-warning-50/50` (semi-transparent)
  - Change border from `border-b border-amber-200` to `border-b border-warning-200/60`
  - Replace "Dismiss" text button with `&times;` icon button
  - Add Alpine `x-transition:leave` for smooth dismiss
  - File: `templates/components/disclaimer_banner.html`

- [x] **3.4 — Update `lang_switcher.html`**
  - Add `transition-colors` to buttons
  - Consider changing `text-border` separator to `text-text-faint`
  - File: `templates/components/lang_switcher.html`

- [x] **3.5 — Visual check: navigation**
  - Verify sidebar logo mark renders correctly
  - Verify left accent bar shows on active page
  - Verify section dividers are visible
  - Verify initials avatar shows (test with user who has first/last name)
  - Test mobile bottom nav: check backdrop-blur works, safe area renders on iOS
  - Test banner dismiss animation

---

### Phase 4 — Pages

Rework individual pages to use the new components and layout patterns.

- [x] **4.1 — Update `base.html` (messages/toasts)**
  - Add `animate-toast-in` class to message divs
  - Add Alpine `x-data="{ show: true }"`, `x-show="show"`, `x-init="setTimeout(() => show = false, 5000)"`
  - Add `x-transition:leave` for smooth exit (opacity + translateY)
  - Change `rounded-lg` to `rounded-xl` on message container
  - File: `templates/base.html`

- [x] **4.2 — Rework `home.html`**
  - Wrap content in `<div class="animate-enter">`
  - Hero: increase heading to `text-[2.5rem] sm:text-5xl md:text-[3.5rem]`, add `leading-[1.1] tracking-tight`
  - Hero: increase vertical padding from `py-12 md:py-16` to `py-16 md:py-24`
  - Hero: increase subtitle spacing from `mt-4` to `mt-6`, constrain to `max-w-lg`
  - Replace CTA button with `btn-primary` class
  - Replace secondary link with `text-text-muted hover:text-text transition-colors` style
  - Pillar cards: remove explicit icon containers (`h-10 w-10 bg-primary-50`), replace with simpler smaller icons
  - "How it works" steps: change numbered circles from `bg-primary-600` to `bg-text` for less primary-color saturation
  - File: `templates/pages/home.html`

- [x] **4.3 — Rework `login.html`**
  - Remove card wrapper (`card_start`/`card_end`)
  - Center form vertically: `flex min-h-[80vh] items-center justify-center`
  - Add logo mark centered above form (rounded-xl bg-primary-600, "L")
  - Change heading from "Login" to "Welcome back"
  - Add subtitle "Sign in to your account" in text-text-muted
  - Apply `.input` class to all form fields (replace inline border/focus classes)
  - Apply `.btn-primary` class to submit button (replace inline bg-primary-600 classes)
  - Constrain form width to `max-w-sm`
  - File: `templates/account/login.html`

- [x] **4.4 — Rework `signup.html`**
  - Same pattern as login: remove card, center vertically, logo mark, `.input`/`.btn-primary` classes
  - Change heading to "Create your account"
  - File: `templates/account/signup.html`

- [x] **4.5 — Rework `logout.html`**
  - Apply same centered card-less pattern if applicable
  - File: `templates/account/logout.html`

- [x] **4.6 — Rework `real_estate/detail.html`**
  - Wrap content in `<div class="animate-enter">`
  - Update page heading: `text-[1.75rem] font-semibold tracking-tight` (replace `text-2xl font-bold`)
  - Replace "Property Value" and "Your Share" cards (Row 1) with a 4-column `stat_card` grid:
    - Value, Equity (with % annotation), Mortgage balance, Your share (with % annotation)
  - Move remaining metric_rows (purchase price, appreciation, etc.) into a detail card below
  - Rearrange layout to 3-column on desktop (`lg:grid-cols-3`):
    - Left 2 cols: charts row, expenses, valuations, sale simulator
    - Right 1 col: ownership card, mortgage card, taxes card
  - Replace "Edit" link with `btn-ghost` class
  - Replace "+ Add expense" / "+ Add tax" / "+ Add valuation" buttons with `btn-ghost` class
  - File: `templates/real_estate/detail.html`

- [x] **4.7 — Rework `real_estate/list.html`**
  - Wrap content in `<div class="animate-enter">`
  - Add `card-interactive` class to property card links for hover lift effect
  - Update heading style: `text-[1.75rem] font-semibold tracking-tight`
  - Replace `btn-primary` inline classes with `.btn-primary` class on "+ Add property" button
  - Replace empty state card with `empty_state.html` include (house icon, title, description, CTA)
  - File: `templates/real_estate/list.html`

- [x] **4.8 — Update `real_estate/notifications.html`**
  - Wrap content in `<div class="animate-enter">`
  - Update heading style: `text-[1.75rem] font-semibold tracking-tight`
  - Change unread notification indicator from `bg-primary-50/50 border-primary-200` to `border-l-[3px] border-l-primary-500 border-border` (left accent bar pattern, consistent with nav)
  - Use `text-text-faint` for timestamp
  - Replace empty state with `empty_state.html` include
  - File: `templates/real_estate/notifications.html`

- [x] **4.9 — Update `real_estate/create.html` and `real_estate/edit.html`**
  - Apply `.input` class to all form fields
  - Apply `.btn-primary` class to submit button
  - Update heading styles
  - Files: `templates/real_estate/create.html`, `templates/real_estate/edit.html`

- [x] **4.10 — Update `real_estate/invite.html`**
  - Apply `.input` class to form fields
  - Apply `.btn-primary` class to submit button
  - Update heading styles
  - File: `templates/real_estate/invite.html`

- [x] **4.11 — Update `real_estate/confirm_remove_owner.html`**
  - Apply `.btn-danger` to confirm button
  - Apply `.btn-ghost` to cancel button
  - File: `templates/real_estate/confirm_remove_owner.html`

- [x] **4.12 — Update real estate partials (forms)**
  - `expense_form.html`: apply `.input` to fields, `.btn-primary` to submit, `.btn-ghost` to cancel
  - `tax_form.html`: same pattern
  - `valuation_form.html`: same pattern
  - Files: `templates/real_estate/partials/expense_form.html`, `tax_form.html`, `valuation_form.html`

- [x] **4.13 — Update real estate partials (lists)**
  - `expense_list.html`: use `font-mono tabular-nums` on amount column, `text-text-faint` on date column
  - `tax_list.html`: same pattern
  - `valuation_history.html`: same pattern
  - `sale_estimate.html`: use `font-mono` on dollar values
  - Files: `templates/real_estate/partials/expense_list.html`, `tax_list.html`, `valuation_history.html`, `sale_estimate.html`

- [x] **4.14 — Update `real_estate/amortization.html`**
  - Apply `font-mono tabular-nums` to table number columns
  - Update heading styles
  - File: `templates/real_estate/amortization.html`

- [x] **4.15 — Update `real_estate/ownership_periods.html`**
  - Update heading styles
  - Apply consistent card/badge styling
  - File: `templates/real_estate/ownership_periods.html`

- [x] **4.16 — Update `pages/dashboard.html`**
  - Wrap content in `<div class="animate-enter">`
  - Update heading styles
  - Apply `font-mono` to financial values
  - File: `templates/pages/dashboard.html`

- [x] **4.17 — Update `portfolio/list.html` and `portfolio/detail.html`**
  - Wrap content in `<div class="animate-enter">`
  - Apply `card-interactive` on list items if clickable
  - Update heading styles
  - Apply `font-mono` to financial values
  - Files: `templates/portfolio/list.html`, `templates/portfolio/detail.html`

- [x] **4.18 — Update `footer.html`**
  - Change `border-border` to `border-border/60` for subtlety
  - Use `text-text-faint` for copyright text (lighter than muted)
  - File: `templates/components/footer.html`

- [x] **4.19 — Update error pages**
  - `404.html`: use `empty_state.html` pattern with a lost icon
  - `500.html`: use `empty_state.html` pattern with an error icon
  - Files: `templates/pages/404.html`, `templates/pages/500.html`

---

### Phase 5 — Polish & QA

Final pass to ensure consistency and catch anything missed.

- [x] **5.1 — Audit all `text-2xl font-bold` occurrences**
  - Grep for `font-bold` in templates — replace with `font-semibold` (600 not 700 is the new standard)
  - Grep for `text-2xl` in headings — replace with `text-[1.75rem] tracking-tight` pattern
  - All templates

- [x] **5.2 — Audit all `rounded-lg` on cards**
  - Grep for `rounded-lg` in card/container contexts — should be `rounded-xl` or `rounded-2xl`
  - Note: keep `rounded-lg` on nav links, badges, small UI elements. Only cards/panels get `rounded-2xl`
  - All templates

- [x] **5.3 — Audit all `bg-gray-*` and `text-gray-*` references**
  - Replace `bg-gray-100` → `bg-bg-subtle`
  - Replace `bg-gray-200` → `bg-bg-subtle` or `bg-border`
  - Replace `text-gray-600` → `text-text-muted`
  - Replace `hover:bg-gray-100` → `hover:bg-bg-hover`
  - All templates

- [x] **5.4 — Audit all `shadow-sm` references**
  - Remove `shadow-sm` from non-elevated cards (depth through borders, not shadows)
  - Keep `shadow-md shadow-black/[0.03]` only on elevated variant
  - All templates

- [x] **5.5 — Audit all inline button styles**
  - Replace `bg-primary-600 px-4 py-2 ... hover:bg-primary-700` patterns with `.btn-primary`
  - Replace text-link buttons with `.btn-ghost`
  - All templates

- [x] **5.6 — Audit all inline input styles**
  - Replace `border border-border px-3 py-2 ... focus:ring-1 focus:ring-primary-500` with `.input`
  - All templates

- [x] **5.7 — Verify `animate-enter` on all page templates**
  - Every `{% block content %}` should wrap its content in `<div class="animate-enter ...">` or `<div class="animate-enter space-y-6">`
  - Check: home, dashboard, login, signup, logout, portfolio list, portfolio detail, real estate list, real estate detail, real estate create/edit, notifications, amortization, ownership periods, invite, confirm remove, 404, 500

- [x] **5.8 — Update `styleguide.html`**
  - Add stat_card and empty_state to the component showcase
  - Update existing component examples to reflect new styles
  - Add a "Buttons" section showing btn-primary, btn-ghost, btn-danger
  - Add an "Inputs" section showing input, input-error states
  - File: `templates/pages/styleguide.html`

- [x] **5.9 — Test responsive behavior**
  - Mobile (375px): bottom nav glass effect, safe area, page entrances
  - Tablet (768px): sidebar appears, content shifts
  - Desktop (1280px): full sidebar, 3-column layouts on detail page
  - Check all pages at each breakpoint

- [x] **5.10 — Test HTMX interactions**
  - Add expense → verify fade-in animation on new list
  - Edit expense → verify form swap is smooth
  - Delete expense → verify list update animates
  - Same for taxes and valuations
  - Sale simulator slider → verify no animation jank
  - Mark notifications as read → verify badge update
  - Verify `hx-swap` targets still work with any markup changes

- [x] **5.11 — Test Alpine.js interactions**
  - Tooltip open/close with enter/leave transitions
  - Disclaimer banner dismiss with fade-out
  - Toast message auto-dismiss after 5 seconds
  - Language switcher still works

- [x] **5.12 — Compile translations**
  - If any user-facing strings changed (e.g., "Welcome back" on login), add them to `locale/fr/LC_MESSAGES/django.po`
  - Run `uv run python manage.py compilemessages`
  - Verify FR translations render correctly

- [x] **5.13 — Verify Containerfile / production build**
  - Run `npm run build` in `frontend/` to verify Vite builds cleanly
  - Verify Tailwind scans all new component files (stat_card.html, empty_state.html)
  - Check that new CSS utility classes (`safe-area-bottom`, component classes) are included in output
  - Run `uv run pytest` to verify no template rendering errors in tests

- [x] **5.14 — Final visual review**
  - Screenshot every page, compare before/after
  - Check for any remaining `gray-*`, `shadow-sm`, `rounded-lg` on cards, or `font-bold` headings
  - Verify the overall feel: warm, precise, crafted — not generic
