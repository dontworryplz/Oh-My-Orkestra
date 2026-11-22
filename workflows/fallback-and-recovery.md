# Fallback & Recovery

## 1. Provider Quota / `429 RESOURCE_EXHAUSTED`

If any provider or `agy` model returns `429 RESOURCE_EXHAUSTED`, auth failure, or timeout:
1. **Report honestly**: State which slot/model failed and why. Never fabricate or extrapolate a review.
2. **Use the verified fallback chain**:
   - `openai-codex/gpt-6.2-sol` -> `openai-codex/gpt-6-luna:max` -> `anthropic/claude-opus-5-5`
   - `openai-codex/gpt-6.2-astra` (`astra-architect`) -> `openai-codex/gpt-6.2-sol` -> `anthropic/claude-opus-5-5`
   - `neon-code-reviewer` (`agy: gemini-4-neon-xhigh`) -> `gemini-4-neon-high` -> `luna-reviewer` (`gpt-6-luna:max`) or `opus-auditor`
   - `hydrogen-debugger` (`agy: gemini-4-hydrogen-xhigh`) -> `gemini-4-hydrogen-high` -> `astra-architect` (`gpt-6.2-astra`)
   - `argon-explorer` (`agy: gemini-4-argon-high`) -> `gemini-3.8-flash-high` -> `luna-explorer` (`gpt-6-luna:max`)
   - `opus-auditor` (`anthropic/claude-opus-5-5`) -> `antigravity-opus-reviewer` (`agy: claude-opus-5-5-high`) -> `neon-code-reviewer`
   - `sonnet-worker` (`anthropic/claude-sonnet-5-5`) -> `antigravity-sonnet-worker` (`agy: claude-sonnet-5-5-high`) -> `luna-worker`

## 2. Partial Worker Failure

- If a parallel writer fails mid-slice, inspect `git status` and `git diff` on its owned files before retrying or reassigning.
- Never run `git reset --hard` or `git checkout -- .` across the repo—dirty user-owned work may exist.

## 3. `agy` CLI Specifics

- If `agy` hangs or times out, re-run with `--print-timeout 180s` and narrower file scope.
- If `agy` rejects `-p`, verify `-p="..."` syntax (prompt attached to flag) via `scripts/agy-run.sh`.
