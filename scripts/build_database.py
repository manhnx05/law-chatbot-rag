#!/usr/bin/env python
"""Build Database Script"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.splitter import main as split_main
from src.core.embedder import main as embed_main
from src.utils.logger import get_logger
from src.config import config

logger = get_logger("build_database", config.paths.logs_dir)


def main():
    logger.info("Building database...")
    
    logger.info("[1/2] Splitting PDF...")
    if split_main() != 0:
        return 1
    
    logger.info("[2/2] Creating embeddings...")
    if embed_main() != 0:
        return 1
    
    logger.info("✓ Database built successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
