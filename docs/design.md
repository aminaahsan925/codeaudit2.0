# LaunchAudit design direction

Round 2 of the UI revamp on `feat/ui-revamp`. UI only: API calls, hooks,
routes and the backend do not change.

## Who it is for

A founder who built an app with AI tools and wants to know if it is safe to
launch. They are smart but not a security engineer. Every screen speaks plain
English first and the technical term second, and ends in one obvious next
action.

Feel: a mature, premium, friendly product. Ink and paper with one cobalt accent, not a violet AI look. Warm and calm, never alarming
until something is wrong, then clear about it.

## What changed from round 1, and why

| Round 1 problem | Round 2 answer |
|---|---|
| App pages looked like long marketing pages | App shell with a sidebar, breadcrumbs and a command palette |
| Landing had no hook; the animation was buried | Hero with a live product card on the right: code scan, findings pop in, verdict |
| Cold teal on near-black, heavy headings | Light first, warm canvas, ink actions, cobalt accent, lighter display type |
| Jargon with no explanation | Plain sentence first, term second, info tips on every term |
| Sample numbers disagreed | One sample dataset in `src/lib/sample-data.ts` |

## Benchmark: what we take

- Linear: the app shell. A quiet sidebar, a command palette, rows that open in place.
- Stripe: a product visual in the hero that explains the product in one look.
- Vercel: live progress as a pipeline you can trust while it runs.
- Raycast: fast, springy feedback on every action.
- Resend: restraint. One brand colour, generous space.

We take qualities, not looks, logos or assets.

## Tokens

### Colour

Light first. Dark mode uses the same roles. No gradients anywhere.

| Role | Light | Dark |
|---|---|---|
| Canvas | `#F6F5F2` warm off-white | `#131210` warm ink |
| Surface (cards) | `#FFFFFF` | `#1B1A18` |
| Sunken (wells, code) | `#EFEDE8` | `#161513` |
| Border | `#E4E1DA` | `#2E2C28` |
| Input outline | `#8A857C` | `#75716A` |
| Ink | `#191817` | `#EEEBE6` |
| Ink muted | `#5F5B55` | `#A8A39B` |
| Primary action | ink `#191817` with `#F6F5F2` text | `#EEEBE6` with ink text |
| Accent, cobalt | `#2348C8` | `#86A4FF` |
| Accent soft / text | `#E8EDFB` / `#1B3AA6` | `#1C2440` / `#BACBFF` |

- Primary buttons are ink, never the accent.
- The cobalt accent appears only on the logo mark, links, the focus ring, the
  active sidebar item and small highlights. In code its tokens are still named
  `brand-*`.
- The final call to action is a dark ink panel with at most a faint accent glow.

Severity and verdict colours are semantic: Critical, High, Medium, Low;
Launch, Fix first, Do not launch. Low is slate (`#55606E`, dark `#9AA6B5`)
so it never reads as the accent. Each is always paired with a word and a shape.

Contrast, measured, both themes:

| Pair | Ratio, at least |
|---|---|
| Ink | 14.6 |
| Muted ink | 5.7 |
| Accent | 6.8 |
| Primary button text | 15.7 |
| Input outlines | 3.3 |
| Severity text on tint | 6.6 |
| Severity marks | 4.9 |

All pass WCAG AA.

### Type

- Display: **Bricolage Grotesque**, weight 500 to 600, tight tracking. Warm and
  a little characterful, which fits a friendly product.
- UI and body: **Instrument Sans**. Clear at small sizes.
- Code only: **IBM Plex Mono**.

Scale: 12, 14, 16, 18, 20, 24, 30, 40, 56 px. Headings use the display face
at weight 550 with -0.025em tracking. Sentence case. No all-caps labels.

### Space, radius, depth

- 4 px grid; steps 4, 8, 12, 16, 24, 32, 48, 64, 96.
- Radius: chips 6, inputs and buttons 10, cards 16, sheets and dialogs 20.
- Shadows, light mode, three layers:
  - `xs` hairline lift for rows
  - `sm` for cards
  - `lg` for floating cards, dialogs, the hero product card

  Dark mode raises surfaces by lightening them instead.
- Blur only on modal overlays: dialogs and the command palette. Sticky bars
  use a near-opaque solid background, because blur on large scrolling areas
  caused jank.
- Cards share one resting elevation (`shadow-card`); only hover lifts them.
- Grid: 12 columns, 1200 px max, 24 px gutters (16 on mobile).
- Breakpoints 640, 768, 1024, 1280. Sidebar collapses below 1024.
- Z-index: header 30, sidebar 30, popover 40, sheet 45, dialog 50, toast 60.

## Layouts

### Marketing, `/` only

1. Sticky translucent header: wordmark, How it works, Checks, FAQ, Open app,
   Run an audit.
2. Hero: headline, one-line promise and two buttons on the left. On the right,
   a live product card in a tilted browser frame: code scans, findings pop in,
   the verdict lands. Faint grid texture behind.
3. Trust strip: what we check, and "Your code is read, never run".
4. Bento grid of checks. Each tile has a plain title, a one-line why, and a
   tiny proof sample.
5. How it works in 3 steps, each with a small visual.
6. Example report preview you can click into.
7. FAQ written for non-technical founders.
8. Final call to action on a dark ink panel.
9. Footer with columns.

### App shell, every other page

- Left sidebar, collapsible:
  - New audit, Reports, Projects, Settings, Help, each with an icon and an
    active state.
  - Projects and Settings are marked "Soon" until those features exist.
  - Help opens the FAQ.
  - On mobile it becomes a drawer.
- Top bar: breadcrumbs, search button that opens the command palette
  (Ctrl/Cmd+K), API status, theme toggle, profile menu ("Guest" until sign-in
  lands).

### Report `/reports/[id]` and shared `/r/[token]`

- Desktop, two columns:
  - Left, sticky: the verdict hero, with a traffic-light verdict, one plain
    sentence, an animated score ring, a severity donut, and before and after
    if this is a rerun.
  - Right: the fix-first list. Each row has a plain title, then the technical
    name, then expandable evidence.
- Sticky action bar: Rerun, PDF, Share. The shared page hides Rerun.
- Mobile: verdict hero first, then the list.

### Run an audit `/audits/new`

A stepper: Code, Live site, Test login, Review. Each step has one help line.
Only Code is required; the others can be skipped. Review shows what will
happen before the Run button.

### Live progress `/audits/[id]`

A pipeline of stages with animated state, and findings counting up by
severity. Finished: verdict reveal and "Open the report". Failed: which stage,
why, and what to do.

### Reports list, sign-in, 404, error

- Reports list: rows with verdict, score and date. Designed empty and loading
  states.
- Sign-in: centred card. It is wired when the Google sign-in branch merges;
  until then the profile menu shows Guest.
- 404 and error: plain sentence, reference id where it exists, two ways forward.

## Plain English first

- Findings lead with what can happen ("Someone can read other users' data"),
  then the term ("Broken access control, CWE-639").
- Every severity, the score, the verdict and each technical term has an info
  tip. Copy lives in `src/lib/glossary.ts`.

## Motion

`motion` (`motion/react`) with `LazyMotion`. Variants live in
`src/components/ui/motion.ts`.

- 150 to 400 ms. Only transform and opacity. Springs for things the user moves.
- Moments:
  - the hero product card sequence
  - reveals as you scroll
  - the score ring count-up
  - the verdict reveal
  - staggered findings, capped at 8
  - sidebar and command palette transitions
  - a small hover lift on cards
- With reduced motion on, everything renders in its final state.

## Performance

No layout shift: skeletons match real sizes, images have fixed ratios. Lazy
load the hero animation's off-screen parts and journey screenshots. Report
the first-load JS change in the PR.
