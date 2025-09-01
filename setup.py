#!/usr/bin/env python3
"""
Setup script for Claude Regulation Scraper
"""
from setuptools import setup, find_packages
import os

# Read README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "AI-powered regulation discovery and monitoring system"

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="claude-regulation-scraper",
    version="1.0.0",
    description="AI-powered regulation discovery and monitoring system",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Claude AI Assistant",
    author_email="noreply@anthropic.com",
    url="https://github.com/your-username/claude-regulation-scraper",
    
    packages=find_packages(),
    include_package_data=True,
    
    install_requires=read_requirements(),
    
    entry_points={
        'console_scripts': [
            'claude-reg=claude_regulation_scraper:cli',
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    
    python_requires=">=3.8",
    
    keywords="regulation scraping ai llm openai compliance monitoring legal",
    
    project_urls={
        "Bug Reports": "https://github.com/your-username/claude-regulation-scraper/issues",
        "Source": "https://github.com/your-username/claude-regulation-scraper",
        "Documentation": "https://github.com/your-username/claude-regulation-scraper/wiki",
    },
)