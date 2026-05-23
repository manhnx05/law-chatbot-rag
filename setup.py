"""Setup script for Law Chatbot RAG"""
from setuptools import setup, find_packages

with open("readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="law-chatbot-rag",
    version="2.0.0",
    description="Professional Vietnamese Labor Law Q&A System using RAG",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Law Chatbot Team",
    python_requires=">=3.8",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "sentence-transformers>=2.2.2",
        "torch>=2.0.0",
        "faiss-cpu>=1.7.4",
        "pymupdf>=1.23.0",
        "streamlit>=1.28.0",
        "requests>=2.25.0",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "slowapi>=0.1.9",
        "numpy>=1.24.0",
        "tqdm>=4.65.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "law-chatbot-build=scripts.build_database:main",
            "law-chatbot-api=scripts.run_api:main",
            "law-chatbot-ui=scripts.run_ui:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
