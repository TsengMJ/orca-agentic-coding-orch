{
  "run_id": "issue-1-20261109T152523Z",
  "issue_number": 1,
  "issue_url": "https://github.com/TsengMJ/agent-wallet/issues/1",
  "issue_title": "Restyle apps/web color system",
  "request": "Restyle `apps/web` color system only.\n\n## Goal\nReplace the CSS variables / background treatment so the dashboard uses a new dark palette:\n- dark slate base\n- electric cyan accent\n- amber warn\n\n## Scope\n- `apps/web/src/index.css` (primary)\n- `apps/web/src/App.css` only if needed for tokens\n- Keep layout, copy, and behavior identical\n- Do **not** change agent API, contracts, or shared packages\n\n## Acceptance\n- Old lime/olive tokens are gone from the web color system\n- `pnpm test` stays green\n- Visual hierarchy remains readable (accent for brand/title, muted for secondary, warn for offline)"
}
