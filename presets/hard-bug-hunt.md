# Preset: Hard Bug Hunt (`hard-bug-hunt`)

1. `orchestra init --no-write` + `trail ask "<bug area>"` -> verify stack and check if a fix was already tried and ruled out.
2. Reproduce failure with exact command/logs (`luna-tester` or `node_repl`).
3. `hydrogen-debugger` (`agy`: `gemini-4-hydrogen-xhigh`, `--auto-fallback`) -> trace trigger -> state -> failure sink, prove root cause with `file:line`, and list sibling call sites.
4. `luna-worker` (or `sonnet-worker`) -> apply minimal source-cause fix + write regression test that fails before and passes after.
5. `neon-code-reviewer` + `trail note --title "<root cause>"` -> verify fix and record learning.
