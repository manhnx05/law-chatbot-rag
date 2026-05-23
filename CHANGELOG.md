# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-XX

### Added
- FastAPI REST API with comprehensive endpoints
- API key authentication (optional)
- Rate limiting for API endpoints (30/min for search, 10/min for query)
- Async support for non-blocking operations
- Retry logic for retriever search operations
- Comprehensive unit tests for core modules
- Environment configuration support (.env file)
- CORS configuration with environment variables
- Metrics tracking for API requests
- Professional logging with colored console output
- API documentation with Swagger UI and ReDoc

### Changed
- Fixed import paths across all modules (from relative to absolute imports)
- Improved project structure with proper src/ layout
- Updated README with API documentation and new features
- Enhanced error handling with better error messages
- Improved configuration management with dataclasses

### Fixed
- Import path issues in api/main.py
- Import path issues in ui/app.py
- Import path issues in core modules (embedder, retriever, splitter)
- Import path issues in utils modules (logger)
- CORS configuration now supports environment variables

### Security
- Added API key authentication
- Configurable CORS origins (no longer allows all origins by default)
- Rate limiting to prevent API abuse

## [1.0.0] - 2024-01-XX

### Added
- Initial release
- PDF splitting functionality
- FAISS vector database
- Vietnamese BERT embeddings
- Streamlit web UI
- Ollama LLM integration
- Basic retrieval and generation pipeline
