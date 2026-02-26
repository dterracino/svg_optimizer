#!/usr/bin/env python3
"""
Quick verification script to check if the package is ready for PyPI.
Run this before building and publishing.
"""
import sys
from pathlib import Path

def check_file_exists(filepath: str, required: bool = True) -> bool:
    """Check if a file exists."""
    path = Path(filepath)
    exists = path.exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    requirement = "REQUIRED" if required else "optional"
    print(f"  {status} {filepath} ({requirement})")
    return exists or not required

def check_package_structure():
    """Verify package structure."""
    print("\n📦 Checking Package Structure...")
    
    all_ok = True
    
    # Required files
    print("\nRequired files:")
    all_ok &= check_file_exists("pyproject.toml")
    all_ok &= check_file_exists("README.md")
    all_ok &= check_file_exists("LICENSE")
    all_ok &= check_file_exists("svg_optimizer/__init__.py")
    all_ok &= check_file_exists("svg_optimizer/__main__.py")
    
    # Optional but recommended
    print("\nRecommended files:")
    check_file_exists("CHANGELOG.md", required=False)
    check_file_exists("MANIFEST.in", required=False)
    check_file_exists("setup.py", required=False)
    check_file_exists("svg_optimizer/py.typed", required=False)
    
    # Package structure
    print("\nPackage structure:")
    all_ok &= check_file_exists("svg_optimizer/upscalers/__init__.py")
    
    return all_ok

def check_pyproject_content():
    """Check pyproject.toml for placeholders."""
    print("\n⚙️  Checking pyproject.toml...")
    
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
        
        issues = []
        
        if "yourusername" in content.lower():
            issues.append("Contains 'yourusername' placeholder - update GitHub URLs")
        
        if 'name = "svg-auto-optimizer"' not in content:
            issues.append("Package name might be incorrect")
        
        if 'version = "0.1.0"' not in content:
            issues.append("Check version number")
        
        if issues:
            print("  ⚠ Issues found:")
            for issue in issues:
                print(f"    - {issue}")
            return False
        else:
            print("  ✓ pyproject.toml looks good")
            return True
            
    except FileNotFoundError:
        print("  ✗ pyproject.toml not found!")
        return False

def check_version_consistency():
    """Check version numbers match across files."""
    print("\n🔢 Checking Version Consistency...")
    
    versions = {}
    
    # Check pyproject.toml
    try:
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.startswith("version = "):
                    versions["pyproject.toml"] = line.split('"')[1]
                    break
    except Exception:
        pass
    
    # Check __init__.py
    try:
        with open("svg_optimizer/__init__.py", "r") as f:
            for line in f:
                if line.startswith("__version__"):
                    versions["__init__.py"] = line.split('"')[1]
                    break
    except Exception:
        pass
    
    if len(versions) == 0:
        print("  ✗ No version found in any file!")
        return False
    
    if len(set(versions.values())) == 1:
        version = list(versions.values())[0]
        print(f"  ✓ All versions match: {version}")
        return True
    else:
        print("  ✗ Version mismatch:")
        for file, ver in versions.items():
            print(f"    {file}: {ver}")
        return False

def main():
    """Run all checks."""
    print("=" * 70)
    print("SVG Auto-Optimizer - PyPI Readiness Check")
    print("=" * 70)
    
    structure_ok = check_package_structure()
    pyproject_ok = check_pyproject_content()
    version_ok = check_version_consistency()
    
    print("\n" + "=" * 70)
    if structure_ok and pyproject_ok and version_ok:
        print("✅ All checks passed! Ready to build.")
        print("\nNext steps:")
        print("  1. Review PYPI_CHECKLIST.md")
        print("  2. Update GitHub URLs if needed")
        print("  3. Run: python -m build")
        print("  4. Run: twine check dist/*")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nSee PYPI_SETUP.md for help.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
