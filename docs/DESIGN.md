# OIST Mock ERP — interface design tokens

The interface should read like a clear campus record: quiet, paper-like, left aligned, and easy to use on a phone. Screens prioritize the next useful action and keep attendance and course data dense without crowding. Every status includes a word or letter alongside its color.

## Color tokens

| Token | Value | Use |
| --- | --- | --- |
| `--color-navy` | `#353A7C` | Main actions, selected navigation, and focus outlines |
| `--color-vermilion` | `#E2332F` | Critical attendance, errors, and destructive actions |
| `--color-marigold` | `#F9D20A` | Small emphasis and selected row markers |
| `--color-paper` | `#FAF7F0` | Page background |
| `--color-ink` | `#15162B` | Primary text |
| `--color-hairline` | `#E2DDD0` | Dividers and outlines |
| `--color-muted` | `#666579` | Secondary labels and supporting text |
| `--color-safe` | `#286548` | Safe attendance with a visible “Safe” label |
| `--color-watch` | `#9A5B00` | Watch attendance with a visible “Watch” label |
| `--color-surface` | `#FFFEFA` | Forms and table surfaces |
| `--color-soft` | `#F0ECE2` | Quiet selected states and read-only fields |
| `--color-white` | `#FFFFFF` | Text on navy actions |

## Typography tokens

| Token | Family | Use |
| --- | --- | --- |
| `--font-heading` | Newsreader | Page titles and large figures |
| `--font-body` | Atkinson Hyperlegible Next | Body, labels, inputs, and navigation |
| `--font-mono` | Spline Sans Mono | Roll numbers, IDs, times, and tabular figures |

Fonts are self-hosted with `@fontsource`; do not use a CDN. The type scale is 12px metadata, 14px compact controls, 16px body, 20px section title, 28px page title, and 36px key figure. Numeric values use tabular figures where supported.

## Spacing and shape tokens

| Token | Value |
| --- | --- |
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-12` | 48px |
| `--radius-control` | 4px maximum |
| `--border-hairline` | 1px solid `--color-hairline` |
| `--content-max` | 1200px |

Use square corners by default, one-pixel borders, no gradients, no blur, and no decorative shadows. Tables stay left aligned and compact. Layout can be asymmetric and should leave room around page titles and major sections. On narrow screens, navigation becomes a bottom bar and tables become stacked, labeled rows.

## Components and iconography

Use regular-weight Phosphor icons with short text labels when an icon might be ambiguous. Do not use emoji as icons. Buttons have clear verbs and visible focus states. Attendance is marked with a two-state P/A control; the letter, text, and selected state remain understandable without color.

Favicon files in `frontend/public/` are derived from the supplied OIST crest. Use the same mark at small size in the application header.
