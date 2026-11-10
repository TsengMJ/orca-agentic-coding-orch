# Git push must use SSH in agents (2026-11-10)

## Failure

`gh_collab publish` committed locally then died on `git push -u origin …` with:
`could not read Username for 'https://github.com': terminal prompts disabled`.

`gh` API worked; only HTTPS git push failed in the non-interactive agent environment.

## Fix

Push product branches with `git@github.com:<owner>/<repo>.git` (`github_ssh_url` / `git_push_head`), not whatever HTTPS URL `origin` happens to be.

## Rule

If a step needs GitHub write without a TTY, use `gh` or SSH remotes — never interactive HTTPS.