#!/usr/bin/env python3
"""
Setup script for Bank Reconciliation System
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="bank-reconciliation-system",
    version="1.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A comprehensive Streamlit-based application for automated bank reconciliation",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/bank-reconciliation-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "bank-recon=app:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
