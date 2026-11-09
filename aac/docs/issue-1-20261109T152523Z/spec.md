# Spec: Agent Wallet web dashboard palette (dark slate / electric cyan / amber)

Product repo: `TsengMJ/agent-wallet`  
Default checkout: `/Users/tsengmingchun/orca/projects/agentic-wallet`  
Issue edit surface: `apps/web/src/index.css` only

This spec is normative. Implementation matches the hex values and the file boundary below. It does not invent a second palette.

## Context / Problem / Goals

`apps/web` is a thin Vite + React dashboard (block cards, agent health, chain table). Color lives in `apps/web/src/index.css` custom properties. `apps/web/src/App.css` only references those variables. `apps/web/src/App.tsx` owns copy, layout class names, and the `/api/health` fetch.

Current `:root` tokens and the body glow are an olive / lime set:

| Token or literal | Current value | Role today |
| --- | --- | --- |
| `--bg` | `#10140f` | Page background |
| `--bg-elev` | `#171d16` | Card background |
| `--line` | `#2a3528` | Card and table borders |
| `--text` | `#e8eee4` | Primary text (green-tinted) |
| `--muted` | `#9aa894` | Secondary text |
| `--accent` | `#c6f25a` | Brand eyebrow (lime) |
| `--accent-2` | `#7ad0c6` | Links and mono paths (teal) |
| `--warn` | `#e7b549` | Offline health line |
| body radial stop | `#1d2a18` | Olive glow behind the page |

`App.css` bindings that define hierarchy (must stay):

- `.eyebrow` → `var(--accent)` (brand line above the title)
- `h1` has no color override → inherited `var(--text)` (page title)
- `.lede`, `.muted` → `var(--muted)` (secondary copy, card notes, chain ecosystem)
- `.warn` → `var(--warn)` (offline health)
- `.mono` and `a` → `var(--accent-2)` (paths and links)
- `.card` → `var(--bg-elev)` and `var(--line)`

Health rendering in `App.tsx` (must stay):

- `health === null` → `<p class="muted">checking /health …</p>`
- `"error" in health` → `<p class="warn">offline — start with \`pnpm dev:agent\`. {error}</p>`
- success → default text `{service} ok · ankr key {set \| public endpoints}`

**Problem.** The dashboard still reads as lime-on-olive. The requested look is a dark slate base, an electric cyan accent, and an amber warn.

**Goal.** Replace those color literals so the same DOM, copy, and behavior paint with the palette in §3.

**User story.** As a reader of the dashboard, I still see the same sections and words, with the brand eyebrow in electric cyan, secondary lines muted, the title in primary text, and the offline line in amber, on a dark slate page.

## Scope / Out of Scope

**In scope**

- Replace the nine color literals in `apps/web/src/index.css` listed in §3 (eight custom properties plus the body radial stop).
- Leave `color-scheme: dark`, the font stack, gradient geometry, and every non-color rule in that file as they are.

**Out of scope**

- Any edit to `apps/web/src/App.css`, `App.tsx`, `App.test.ts`, `main.tsx`, `index.html`, or any file outside `apps/web/src/index.css`.
- Layout, spacing, breakpoints, copy, class names, route behavior, and the `/api/health` fetch.
- Agent API (`apps/agent`), `packages/shared`, EVM contracts, Solana programs, and their tests.
- Renaming custom properties or classes. Adding a light theme, a CSS framework, a token package, remote fonts, images, or `url()` assets.
- New or modified unit tests and screenshot sign-off. Color acceptance is source inspection plus the existing `pnpm test` command.
- Timeout, retry, cancel, and concurrency behavior. This issue does not change control flow.
- Loading "IBM Plex Sans" (it is named in the font stack and is not linked from `index.html`). The font stack stays as written.

## Interfaces and Behaviors

**CSS interface (the only one this issue changes).** `:root` in `apps/web/src/index.css` keeps these property names and `color-scheme: dark`. Values become:

| Property | New value | Hue role |
| --- | --- | --- |
| `--bg` | `#0f1419` | Dark slate page |
| `--bg-elev` | `#1a2330` | Elevated slate card |
| `--line` | `#2e3c4e` | Slate border |
| `--text` | `#e7eef6` | Cool primary text |
| `--muted` | `#8fa0b3` | Muted secondary text |
| `--accent` | `#22d3ee` | Electric cyan (brand eyebrow) |
| `--accent-2` | `#67e8f9` | Lighter cyan (links, mono) |
| `--warn` | `#f59e0b` | Amber (offline) |

`font-family` stays `"IBM Plex Sans", "Segoe UI", sans-serif`. `background` stays `var(--bg)`. `color` stays `var(--text)`.

**Background treatment.** The `body` rule stays a two-layer background. Geometry stays `radial-gradient(1200px 500px at 10% -10%, <stop> 0%, transparent 55%)`, then `var(--bg)`. The stop changes from `#1d2a18` to `#163044` (slate glow). No extra gradient layers.

**Unchanged rules in `index.css`.** The `*`, `html, body, #root`, `a`, and `button` rules stay as they are today, including `a { color: var(--accent-2); }`.

**Unchanged component contract (`App.css` / `App.tsx`).** Hierarchy after the token swap:

| Surface | Class / element | Resolves to |
| --- | --- | --- |
| Brand line "account abstraction / agent wallet" | `.eyebrow` | `#22d3ee` on `#0f1419` |
| Title "Agent Wallet" | `h1` | `#e7eef6` on `#0f1419` |
| Lede, card notes, ecosystem, "checking /health …" | `.lede` / `.muted` | `#8fa0b3` |
| Paths and links | `.mono` / `a` | `#67e8f9` |
| Cards and chain table borders | `.card` / `.table` / `.row` | background `#1a2330` or transparent, border `#2e3c4e` |
| Offline health | `.warn` | `#f59e0b` on `#1a2330` |
| Healthy agent line | plain `<p>` | `#e7eef6` |

No JavaScript, JSON, or HTTP interface changes. `/api` still proxies to the agent. Chain rows still come from `@agent-wallet/shared`.

## Acceptance Criteria (AC-01, AC-02, … — each observable PASS/FAIL)

Hex compare is case-insensitive. Whitespace-only edits and any other edit fail the diff AC.

### AC-01 — `:root` tokens

Observe `apps/web/src/index.css` `:root`.

- PASS when `color-scheme` is `dark` and the eight properties equal the §3 table (`--bg` `#0f1419`, `--bg-elev` `#1a2330`, `--line` `#2e3c4e`, `--text` `#e7eef6`, `--muted` `#8fa0b3`, `--accent` `#22d3ee`, `--accent-2` `#67e8f9`, `--warn` `#f59e0b`), each declared once, and `font-family`, `background: var(--bg)`, and `color: var(--text)` are unchanged.
- FAIL when any name is missing, renamed, duplicated, or set to a different value, or `color-scheme` is not `dark`.

### AC-02 — Body glow

Observe the `body` background in `apps/web/src/index.css`.

- PASS when it is exactly a `radial-gradient(1200px 500px at 10% -10%, #163044 0%, transparent 55%)` layered over `var(--bg)`, with no other background images or colors.
- FAIL when the olive stop `#1d2a18` remains, the stop is not `#163044`, or the geometry changes.

### AC-03 — Old lime / olive / retired literals are gone

Search `apps/web` for these literals (case-insensitive): `#10140f`, `#171d16`, `#2a3528`, `#e8eee4`, `#9aa894`, `#c6f25a`, `#7ad0c6`, `#e7b549`, `#1d2a18`.

- PASS when none occur under `apps/web`.
- FAIL when any occur. `#c6f25a` and the olive neutrals and glow are the old lime/olive system. `#7ad0c6` and `#e7b549` are retired by the cyan and amber replacements in §3.

### AC-04 — Hierarchy bindings stay on the same variables

Observe `apps/web/src/App.css` and the `a` rule in `index.css`. They must match the current file bytes (no diff).

- PASS when `.eyebrow` uses `var(--accent)`, `.lede` and `.muted` use `var(--muted)`, `.warn` uses `var(--warn)`, `.mono` uses `var(--accent-2)`, `.card` uses `var(--bg-elev)` and `var(--line)`, `a` uses `var(--accent-2)`, and `h1` still has no `color` declaration.
- FAIL when a binding is retargeted, a color is hardcoded in `App.css`, or `h1` is painted with `--accent`.

### AC-05 — Single-file diff

Diff the agent-wallet checkout against the pre-change tree for this issue.

- PASS when the only content change is in `apps/web/src/index.css`, and that diff only replaces the nine hex literals in §3 (`#10140f`→`#0f1419`, `#171d16`→`#1a2330`, `#2a3528`→`#2e3c4e`, `#e8eee4`→`#e7eef6`, `#9aa894`→`#8fa0b3`, `#c6f25a`→`#22d3ee`, `#7ad0c6`→`#67e8f9`, `#e7b549`→`#f59e0b`, `#1d2a18`→`#163044`).
- FAIL when any other file changes, or `index.css` changes outside those nine substitutions (including added selectors, a light-mode `@media`, or a new stylesheet).

### AC-06 — Readable contrast floors

Using WCAG 2.x relative luminance, compute contrast for the §3 hex pairs. This is the readable-hierarchy check. No screenshot is required.

| Pair | Floor |
| --- | --- |
| `--text` `#e7eef6` on `--bg` `#0f1419` | ≥ 7:1 |
| `--text` `#e7eef6` on `--bg-elev` `#1a2330` | ≥ 7:1 |
| `--muted` `#8fa0b3` on `--bg` `#0f1419` | ≥ 4.5:1 |
| `--muted` `#8fa0b3` on `--bg-elev` `#1a2330` | ≥ 4.5:1 |
| `--accent` `#22d3ee` on `--bg` `#0f1419` | ≥ 4.5:1 |
| `--accent-2` `#67e8f9` on `--bg` `#0f1419` | ≥ 4.5:1 |
| `--accent-2` `#67e8f9` on `--bg-elev` `#1a2330` | ≥ 4.5:1 |
| `--warn` `#f59e0b` on `--bg-elev` `#1a2330` | ≥ 4.5:1 |

- PASS when every pair meets its floor (expected with the §3 values: about 15.8, 13.5, 6.9, 5.9, 10.2, 12.8, 10.9, and 7.4).
- FAIL when any pair is below its floor.

### AC-07 — `pnpm test` stays green

From the agent-wallet repository root, run `pnpm test`.

- PASS when the process exit code is 0. Existing skips (Solana tests skipped when Anchor is absent, per the product README) still count as pass if the command exits 0.
- FAIL when the exit code is non-zero. Do not edit tests, `apps/agent`, `packages/shared`, or contracts to force a pass.

## Failure / Edge Cases

This change has no new runtime branch. Failure means the CSS diff missed the contract.

| Case | Expected |
| --- | --- |
| One token updated, another left olive or lime | FAIL AC-01 and AC-03. No mixed palette. |
| Variables renamed or a fallback like `var(--accent, #c6f25a)` added | FAIL AC-01 and AC-03. Names stay bare `var(--name)` as today. |
| Radial geometry kept but olive stop left in place | FAIL AC-02 and AC-03. |
| `App.css` inlined with hex so tokens no longer drive the UI | FAIL AC-04 and AC-05. |
| `App.tsx` copy, class names, or `/api/health` handling edited | FAIL AC-05. Offline text must still be the `.warn` node; the checking state must still be `.muted`. |
| A `prefers-color-scheme: light` block or a second theme added | FAIL AC-05. Dark only. |
| New CSS file or `url()` / remote font added | FAIL AC-05. |
| Hex written in uppercase (`#22D3EE`) | PASS AC-01 if the value matches case-insensitively, and the rest of the diff is only those substitutions. |
| `pnpm test` fails because this edit broke the web package | FAIL AC-07. Fix by restoring the CSS contract, not by changing tests. |
| `pnpm test` fails in agent, shared, or contracts with no CSS relationship | Out of scope to repair those packages. AC-07 still fails the issue until the command exits 0. Do not expand the diff to chase an unrelated red test. |
| Health request hangs, 5xx, or offline | Unchanged `App.tsx` behavior: reject path renders `.warn` with the existing sentence plus the error message. No new timeout. |
| Duplicate mounts or concurrent fetches | Unchanged. One `useEffect` fetch on mount. Not modified. |

## Backward Compatibility / Regression Targets

- **Intentional visual break:** lime accent, olive surfaces, teal `--accent-2`, and the previous warn gold are replaced. That is the request.
- **Stable names:** `--bg`, `--bg-elev`, `--line`, `--text`, `--muted`, `--accent`, `--accent-2`, `--warn` stay so current `var()` callers keep resolving.
- **Stable DOM and copy:** header, three block cards, health card, chain table, English strings, and the `720px` single-column `.row` breakpoint stay.
- **Stable behavior:** `fetch("/api/health")`, chain list from `@agent-wallet/shared` (`CHAINS`, `rpcUrlFor`), and `apps/web/src/App.test.ts` (both ecosystems, `solana_devnet` present) stay green via AC-07 without editing that test.
- **No migration.** No stored theme, no user setting, no cache key. Reload picks up the stylesheet.
- **Neighbors untouched:** `apps/agent`, `packages/shared`, `contracts/evm`, `contracts/solana`.

## Security / Reliability Requirements

- Stylesheet literals only. Do not add network access, `url()`, remote styles, or inline scripts.
- Do not read or write `.env`, keys, or RPC credentials. Ankr key display copy stays in `App.tsx` and is not edited.
- Do not change the `/api` proxy, health payload handling, or link targets.
- `color-scheme: dark` stays so the page does not flip to a light UA scheme.
- Contrast floors in AC-06 are the reliability bar for brand, secondary, and offline text.
- No new dependency and no change to `package.json` scripts.

## Assumptions and Open Questions

Resolved by this spec (not open, not `Requires Human Decision`):

1. **Normative hex.** "Dark slate / electric cyan / amber" is implemented only as the §3 table. Another brand hex is a spec edit, not an implementer choice.
2. **Title color.** The page title stays `--text`. "Accent for brand/title" means the brand eyebrow stays `--accent` and the title stays high-contrast primary text. `h1` is not recolored.
3. **`--accent-2`.** Links and mono paths move from `#7ad0c6` to `#67e8f9` so the accent family is cyan and still distinct from the eyebrow.
4. **Warn hex.** `#e7b549` is replaced by `#f59e0b`. The offline role stays `.warn`.
5. **Glow.** `#163044` replaces `#1d2a18`. Gradient size and position stay.
6. **`App.css` is not edited.** Tokens already live in `index.css`. The "only if needed" clause is not needed.
7. **Checkout.** Edits apply to the `TsengMJ/agent-wallet` tree under orchestration. Default path is `/Users/tsengmingchun/orca/projects/agentic-wallet`. Relative paths are from that repo root.
8. **Tests.** No new test file is required. AC-01 through AC-06 are source-observable. AC-07 is the existing root `pnpm test`.

**Open questions:** none. Nothing in this issue is `Requires Human Decision`.

## Risks / Rollback

| Risk | Mitigation |
| --- | --- |
| A near-slate hex slips through and drops contrast under AC-06 | AC-01 locks the hex. AC-06 locks the floors. |
| Olive glow survives a variable-only edit | AC-02 and AC-03 name `#1d2a18` and `#163044`. |
| A drive-by edit in `App.tsx` or shared packages | AC-05 limits the diff to nine hex substitutions in `index.css`. |
| `pnpm test` is red for an unrelated package | Do not widen the diff. AC-07 stays failed until the command exits 0 without out-of-scope edits. |

**Rollback.** Restore `apps/web/src/index.css` to the pre-change blob (the nine old literals in §1). No data migration, no API rollback, no feature flag. Reload is enough after the file is restored.
