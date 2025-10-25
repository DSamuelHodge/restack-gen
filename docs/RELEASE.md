# Release Process (v1.0.0)

This document outlines how to cut a release and publish artifacts.

## Preconditions

- Version in `pyproject.toml` is correct (e.g., `1.0.0`).
- CHANGELOG.md is updated with the release notes.
- All tests green locally and in CI.

## 1) Build artifacts

```bash
python -m pip install --upgrade build
python -m build
```

Artifacts are created under `dist/` (wheel and sdist).

Optional sanity check:

```bash
python - <<'PY'
import zipfile, sys
from pathlib import Path
wheel = max(Path('dist').glob('*.whl'), key=lambda p: p.stat().st_mtime)
print('Wheel:', wheel)
with zipfile.ZipFile(wheel) as z:
    for n in z.namelist():
        if 'restack_gen/templates/' in n:
            print('TEMPLATE:', n)
PY
```

## 2) Tag the release

```bash
git status # ensure clean working tree
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

## 3) (Optional) Publish to PyPI

```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

## 4) Create GitHub release

- Title: `v1.0.0`
- Tag: `v1.0.0`
- Changelog: paste the `1.0.0` section from CHANGELOG.md
- Attach artifacts if desired (usually not needed if publishing to PyPI)

## 5) Post-release

- Verify `pip install restack-gen` pulls the new version.
- Announce release notes.

## Notes

- Avoid duplicating template includes in build config; verify clean builds with no warnings.
- Keep sdist minimal but sufficient: include `restack_gen`, docs, examples, tests, README, LICENSE, CHANGELOG.
