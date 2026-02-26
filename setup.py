#!/usr/bin/env python
"""
Setup script for SVG Auto-Optimizer.

For modern installations, use:
    pip install .

For development:
    pip install -e ".[dev]"

For CPU-only installation:
    pip install ".[cpu]"

For GPU-accelerated installation:
    pip install ".[gpu]"
"""

from setuptools import setup

# All configuration is in pyproject.toml
# This file exists for backwards compatibility with older pip versions
if __name__ == "__main__":
    setup()
