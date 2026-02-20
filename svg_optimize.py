#!/usr/bin/env python3
"""
SVG Optimizer - Convenience wrapper script.

This just delegates to the __main__.py in the package.
You can run this directly or use: python -m svg_optimizer
"""
from svg_optimizer.__main__ import main
import sys

if __name__ == '__main__':
    sys.exit(main())
