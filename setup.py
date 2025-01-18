"""
Setup script for news-scraper with separate dependency groups.
"""
from setuptools import setup, find_packages

# Core dependencies required for both scraping and web
base_requirements = [
    "beautifulsoup4==4.12.3",
    "bs4==0.0.2",
    "requests==2.32.3",
    "selenium==4.27.1",
    "pandas==2.2.3"
]


# Development and testing dependencies
dev_requirements = [
    "pytest==8.0.0"
]

setup(
    name="school-scraper",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=base_requirements,
    extras_require={
        "dev": dev_requirements
        # Full installation with all dependencies
    },
    author="Mateo Fleitas",
    description="A school scraper",
    keywords="schools, scraper, crawler"
)
