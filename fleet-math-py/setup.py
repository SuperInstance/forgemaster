#!/usr/bin/env python3
"""Setup file for fleet-math. See pyproject.toml for project metadata."""

from setuptools import setup, find_packages

setup(
    name="fleet-math",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24",
    ],
    extras_require={
        "test": [
            "pytest>=7",
            "hypothesis>=6",
        ],
    },
    author="Cocapn Fleet",
    description="Cyclotomic field, Eisenstein, and Penrose tiling operations",
    license="MIT",
)
