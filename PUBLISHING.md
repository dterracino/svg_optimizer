# Publishing to PyPI

This guide explains how to build and publish the svg-auto-optimizer package to PyPI.

## Prerequisites

1. Install build tools:

```bash
pip install --upgrade build twine
```

1. Create accounts on:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

## Building the Package

1. Clean previous builds:

```bash
# Windows PowerShell
Remove-Item -Recurse -Force dist, build, *.egg-info

# Linux/Mac
rm -rf dist build *.egg-info
```

1. Build the distribution packages:

```bash
python -m build
```

This creates:

- `dist/svg_auto_optimizer-0.1.0.tar.gz` (source distribution)
- `dist/svg_auto_optimizer-0.1.0-py3-none-any.whl` (wheel)

## Testing the Package

### Test Installation Locally

```bash
# Create a test environment
python -m venv test_env
test_env\Scripts\activate  # Windows
# or
source test_env/bin/activate  # Linux/Mac

# Install the built package
pip install dist/svg_auto_optimizer-0.1.0-py3-none-any.whl

# Test it works
svg-optimizer --help
```

### Upload to TestPyPI

```bash
# Upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ svg-auto-optimizer
```

Note: The `--extra-index-url` is needed because TestPyPI doesn't have all dependencies.

## Uploading to PyPI

Once testing is complete:

```bash
# Upload to production PyPI
python -m twine upload dist/*
```

You'll be prompted for your PyPI credentials, or you can configure them in `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-YOUR-API-TOKEN-HERE

[testpypi]
username = __token__
password = pypi-YOUR-TEST-API-TOKEN-HERE
```

## Post-Publication

1. Verify the package page: <https://pypi.org/project/svg-auto-optimizer/>
2. Test installation: `pip install svg-auto-optimizer`
3. Create a git tag: `git tag v0.1.0 && git push --tags`
4. Create a GitHub release with the changelog

## Updating the Package

1. Update version in `pyproject.toml` and `svg_optimizer/__init__.py`
2. Update `CHANGELOG.md` with changes
3. Build and test as above
4. Upload new version

## Common Issues

### "File already exists"

- You cannot re-upload the same version number
- Increment the version number in `pyproject.toml`

### Missing dependencies

- Ensure all dependencies are listed in `pyproject.toml`
- Test in a clean virtual environment

### Import errors

- Check that `packages` in `pyproject.toml` includes all subpackages
- Verify `__init__.py` files exist in all package directories
