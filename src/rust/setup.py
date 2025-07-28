#!/usr/bin/env python3
"""
Setup script for the Rust Python extension module.
"""

from setuptools import setup, Extension
from setuptools_rust import RustExtension

setup(
    name="dataset_core_rust",
    version="0.1.0",
    description="High-performance data processing with Rust",
    author="Dataset Cleaner Team",
    author_email="team@example.com",
    rust_extensions=[RustExtension("dataset_core_rust")],
    install_requires=["numpy"],
    zip_safe=False,
) 