# Preset: Hard Bug Hunt (`hard-bug-hunt`)

Runbook for non-obvious bugs: race conditions, state corruption, intermittent failures, wrong numbers, "works locally, fails in prod". Optimized to prevent speculative patching.

## Phase 0 — Bootstrap

```bash
orchestra init --no-write          # confirm stack without writing files
trail ask "<bug area>" --source    # has someone already chased this?
git status --short                 # know what is already dirty before touching anything
```

## Phase 1 — Reproduce, don't theorize

- Capture the **exact** failing command, input, and full error/stack (not a paraphrase).
- `luna-tester` or `node_repl` runs the smallest reproduction.
- Record: expected vs actual, environment, frequency (always / intermittent), first-seen commit if bisectable.
- If it cannot be reproduced yet, the bug is "unknown", not "fixed by inspection".

## Phase 2 — Root cause evidence

`hydrogen-debugger` (`agy --role hydrogen-debugger --auto-fallback --mode plan`):

- Trace trigger → intermediate state → failure sink; every hop cites `file:line` + symbol.
- Rule out competing hypotheses explicitly ("it is not the cache because X").
- List sibling call sites sharing the same pattern — bugs cluster.
- Produce the minimal source-cause fix spec and the exact regression test that fails before / passes after.

Escalate to `argon-explorer` when the trace exceeds one module or the log corpus is large (1M context).

## Phase 3 — Fix

`luna-worker` or `sonnet-worker` on owned files only:

- Fix source cause, not symptom; migrate every caller; delete obsolete paths.
- Write the regression test first when feasible, prove it fails, then make it pass.
- No opportunistic refactors inside a bugfix unless the refactor *is* the fix.

## Phase 4 — Verify

1. Regression test passes; test previously failed (state that you observed both).
2. `orchestra review --staged --auto-fallback` → structured Neon verdict.
3. `security-reviewer` if the bug was auth/tenant/data related.
4. `perf-profiler` if it was a timeout/latency bug — confirm the fix isn't masking an N+1.
5. `trail note` the true root cause:

```bash
trail note --title "<plain-language root cause>" <<'EOF'
## Decided
- ...

## Tried and ruled out
- ... (why each false lead was false)

In the code:
- `path/to/file.ext:symbol`
EOF
```

## Anti-Patterns

- Editing several suspicious places at once (destroys causality).
- "Try/catch + retry" without naming the failure mode.
- Claiming a fix without a failing-before/passing-after observation.
- Trusting a model opinion over a reproduced command.
