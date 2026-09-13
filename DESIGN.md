# MetroSensUnlock design

## Brand essence
An offline utility for Metro Exodus players. Quiet, direct and readable. SLEEP is the author alias. The interface explains file selection, sensitivity and manual installation without promotional claims.

## Product principles
One self-contained HTML file. No external fonts, images, scripts, network calls, storage or dependencies. Read only files explicitly selected by the player. Generate downloads rather than overwriting originals. Unsupported and partial executables produce no patched download.

## Palette
The CSS variables in MetroSensUnlock.html are authoritative. Respect the OS light/dark preference across the whole page.

| Token | Light | Dark | Use |
|---|---|---|---|
| background | #f4f5f3 | #151815 | Page |
| panel | #ffffff | #202520 | Form |
| text | #202820 | #eef2e9 | Primary text |
| muted | #536050 | #b1bdae | Supporting text |
| accent | #315b38 | #b7d89b | Links, focus, action |
| on-accent | #ffffff | #182218 | Action text |
| line | #7c8879 | #768671 | Input borders |
| error | #9e2323 | #ffb4ab | Error text |

Text contrast must meet 4.5:1 against its background. Controls and focus outlines must meet 3:1. Verify actual values in the self-check.

## Typography
Use Segoe UI with system-ui and sans-serif fallbacks. Display 40px/650, section heading 22px/650, body 16px/400, caption 14px/400. Use system monospace for filenames and the diagnostic report. No font assets.

## Layout
Maximum width 1040px. A narrow introduction and instruction column sits beside the form. Collapse to one column below 800px. Spacing follows an 8px rhythm. Form sections use separators, not nested cards. All controls use a 6px radius.

## Components
Native file inputs, labelled number inputs and ranges, one preparation button, download links, a backup confirmation checkbox and native details for technical diagnostics. Each has default, focus, disabled and error states where applicable. Outputs disappear whenever input changes. Preparation never claims installation succeeded.

## Motion
No entrance or continuous animation. Button hover and active feedback may use a 120ms ease-out colour transition. Disable transitions for reduced motion.

## Iconography
No icon library or decorative symbols. Text labels carry every action.

## Accessibility
WCAG AA contrast, visible keyboard focus, native controls, status announcements and associated error text. Numeric fields allow precise values without dragging. Layout must work at 200% zoom and 360px width. English copy only in this release.

## Do and don't
Keep local processing and manual installation explicit. Never suggest disabling security software. Do not promise Nexus acceptance. No forced motion, novelty typography or hidden content required for recovery.

## Reference
MetroSensUnlock.html owns the CSS tokens. README.md owns installation and compatibility claims. This contract follows the approved offline HTML rebuild, 2026-09-13.
