# PyPI Release Checklist

Use this checklist before publishing to PyPI.

## Pre-Release Checks

### Code Quality

- [ ] All tests pass (if you have tests)
- [ ] No TODO or FIXME comments in critical code
- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have docstrings
- [ ] No debugging print statements left in code

### Documentation

- [ ] README.md is up to date
- [ ] CHANGELOG.md updated with version and changes
- [ ] All examples in README work correctly
- [ ] License information is correct
- [ ] GitHub repository URL updated in pyproject.toml (if applicable)
- [ ] Author information is correct

### Package Configuration

- [ ] Version number updated in:
  - [ ] `pyproject.toml`
  - [ ] `svg_optimizer/__init__.py` (__version__)
- [ ] Dependencies are correct and version-pinned appropriately
- [ ] Optional dependencies (cpu, gpu, dev) are complete
- [ ] Console scripts entry point is correct
- [ ] Package classifiers are accurate
- [ ] Keywords are relevant

### Files Present

- [ ] `pyproject.toml` (package metadata)
- [ ] `setup.py` (backwards compatibility)
- [ ] `LICENSE` file
- [ ] `README.md`
- [ ] `CHANGELOG.md`
- [ ] `MANIFEST.in`
- [ ] `svg_optimizer/py.typed` (type hints marker)
- [ ] All `__init__.py` files in package directories

### Build & Test

- [ ] Clean previous builds: `rm -rf dist/ build/ *.egg-info/`
- [ ] Build package: `python -m build`
- [ ] Check build output - no warnings or errors
- [ ] Install in fresh venv: `pip install dist/*.whl`
- [ ] Test CLI works: `svg-optimizer --help`
- [ ] Test basic functionality with sample image
- [ ] Test import: `python -c "import svg_optimizer; print(svg_optimizer.__version__)"`

### Upload to TestPyPI

- [ ] Upload: `python -m twine upload --repository testpypi dist/*`
- [ ] Install from TestPyPI in fresh venv
- [ ] Verify package page on test.pypi.org
- [ ] Test installation: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ svg-auto-optimizer`
- [ ] Run basic tests again

## Release

- [ ] Upload to PyPI: `python -m twine upload dist/*`
- [ ] Verify on pypi.org: <https://pypi.org/project/svg-auto-optimizer/>
- [ ] Install from PyPI: `pip install svg-auto-optimizer`
- [ ] Test installation works

## Post-Release

- [ ] Create git tag: `git tag v0.1.0`
- [ ] Push tag: `git push --tags`
- [ ] Create GitHub release with changelog
- [ ] Announce release (social media, forums, etc.)
- [ ] Update documentation/website if applicable
- [ ] Close milestone/issues related to this release

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- MAJOR.MINOR.PATCH (e.g., 0.1.0)
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes (backwards compatible)

First stable release should be 1.0.0
Pre-releases: 0.x.x (current stage)
