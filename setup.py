"""
EGS Print Service - Setup Script
================================

Install: pip install .
Install dev: pip install -e .
Install from GitHub: pip install git+https://github.com/marcenggist/egs-print-service.git
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="egs-print-service",
    version="1.1.0",
    author="EGS Software AG",
    author_email="marc@egs.ch",
    description="Multi-brand printer management service for label and badge printing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcenggist/egs-print-service",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "egs_print_service": ["web/*", "web/**/*"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Printing",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "evolis": ["pywin32>=306"],
        "dev": ["pytest", "pytest-cov", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "egs-print-service=egs_print_service.__main__:main",
        ],
    },
)
