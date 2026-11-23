# Pull Request

## What changed

<!-- One paragraph. Link the issue: Closes #123 -->

## Why

<!-- The failure mode this fixes. "Cleaner" is not a reason; lost context, unsafe diff, wrong output, cost blowup are. -->

## Type

- [ ] Bug fix
- [ ] New CLI command / script behaviour
- [ ] New role or agent
- [ ] Preset / workflow / docs
- [ ] Install / CI / packaging

## Verification

Paste real output, not intent.

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
bash -n install.sh bin/orchestra scripts/*.sh hooks/pre-commit
python3 -m py_compile scripts/*.py
./install.sh --dry-run
orchestra verify --dry-run
```

<details>
<summary>Output</summary>

```
<paste>
```

</details>

## Checklist

- [ ] No model ID that is absent from the live roster (`orchestra doctor`)
- [ ] Docs match behaviour (commands runnable as written, links resolve)
- [ ] Exit codes / JSON contract changes are documented in `CHANGELOG.md`
- [ ] New or changed script logic has a test
- [ ] No secrets, tokens, private paths, or real customer data in the diff
- [ ] `orchestra guard`-style ownership respected (one logical change per PR)
- [ ] Destructive/billable capability changes called out explicitly above
