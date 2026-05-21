"""Setup script for Law Chatbot RAG"""
from setuptools import setup, find_packages

setup(
    name="law-chatbot-rag",
    version="2.0.0",
    description="Professional Vietnamese Labor Law Q&A System using RAG",
    author="Law Chatbot Team",
    python_requires=">=3.8",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "law-chatbot-build=scripts.build_database:main",
            "law-chatbot-api=scripts.run_api:main",
            "law-chatbot-ui=scripts.run_ui:main",
        ],
    },
)
