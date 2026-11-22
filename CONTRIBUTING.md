# Contributing to Oh-My-Orkestra

## Adding a New Role or Agent

1. **AGY CLI role:** Add the role entry in `config/roles.json` with ordered `models`, `mode` (`plan` or `auto`), `allow_nesting`, and `instructions`.
2. **OMP agent:** Add `omp-agents/<role>.md` with Step 0 (`.orchestra/REPO_MAP.md` + `trail ask`), priority order, and output contract.
3. **Config mapping:** Register the override in `config/config.example.yml`.
4. **Tests:** Add coverage in `tests/test_agy_agent.py` and run:
   ```bash
   python3 -m unittest discover -s tests -p "test_*.py" -v
   bash -n install.sh bin/orchestra scripts/*.sh hooks/pre-commit
   ```
5. **Docs:** Update `topology/role-matrix.md` and `README.md`.
