# CI/CD Pipeline

## Sonar Simulation Pipeline

**File:** `pipeline-ci.yml`

- **Push to main:** lint + test (py3.9-3.12) + build
- **Tag v\*:** lint + test + build sdist + manylinux wheels + publish to PyPI
- **PR:** lint + test only

### Release

```bash
git tag v1.1.0
git push origin v1.1.0
# → CI publishes to PyPI automatically
```

### Requirements

- PyPI trusted publishing via GitHub OIDC (set up in pypi.org dashboard)
- Environment `pypi` in repo settings (or change name in workflow)
