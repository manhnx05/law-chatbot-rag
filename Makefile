.PHONY: help install build api ui test clean

help:
	@echo "Law Chatbot RAG - Commands"
	@echo "=========================="
	@echo "make install    - Install dependencies"
	@echo "make build      - Build database"
	@echo "make api        - Run FastAPI server"
	@echo "make ui         - Run Streamlit UI"
	@echo "make test       - Run tests"
	@echo "make clean      - Clean generated files"

install:
	pip install -r requirements.txt

build:
	python scripts/build_database.py

api:
	python scripts/run_api.py

ui:
	python scripts/run_ui.py

test:
	python -m pytest tests/ -v

clean:
	rm -rf storage/articles/*.txt
	rm -f storage/law_index.faiss
	rm -f storage/law_metadata.json
	rm -rf logs/*.log
