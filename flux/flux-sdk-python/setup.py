"""Setup script for flux-constraint SDK."""

from setuptools import setup, find_packages

setup(
    name="flux-constraint",
    version="0.3.0",
    description="FLUX constraint checker SDK with GPU acceleration",
    author="SuperInstance",
    python_requires=">=3.10",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "flux-check=flux.checker:FluxChecker",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
