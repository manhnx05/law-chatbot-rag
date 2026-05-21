"""
PDF Splitter - Extract and split law articles from PDF
"""
import fitz
import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config import config
from utils.logger import get_logger

logger = get_logger("split_law", config.paths.logs_dir)


class PDFSplitter:
    """Extract and split law articles from PDF"""
    
    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.article_pattern = re.compile(
            r"^Điều\s+\d+[a-zA-Z]?\.\s*[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯ]"
        )
    
    def extract_text(self) -> str:
        """
        Extract text from PDF
        
        Returns:
            Extracted text content
        
        Raises:
            FileNotFoundError: If PDF file not found
            Exception: If PDF extraction fails
        """
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        
        try:
            logger.info(f"Opening PDF: {self.pdf_path}")
            doc = fitz.open(self.pdf_path)
            text = ""
            
            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text("text")
                text += page_text + "\n"
                logger.debug(f"Extracted page {page_num}/{len(doc)}")
            
            doc.close()
            logger.info(f"Successfully extracted {len(text)} characters from {len(doc)} pages")
            return text
            
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            raise
    
    def split_articles(self, text: str) -> List[Dict[str, str]]:
        """
        Split text into individual articles
        
        Args:
            text: Full text content
        
        Returns:
            List of articles with title and content
        """
        lines = text.split('\n')
        articles = []
        current_title = ""
        current_content = []
        in_article = False
        
        logger.info("Splitting text into articles...")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            if self.article_pattern.match(line):
                # Save previous article
                if in_article and current_title:
                    articles.append({
                        "title": current_title,
                        "content": "\n".join(current_content).strip()
                    })
                    logger.debug(f"Found article: {current_title}")
                
                # Start new article
                current_title = re.sub(r"\s+", " ", line).strip()
                if not current_title.endswith("."):
                    current_title += "."
                current_content = []
                in_article = True
            else:
                if in_article:
                    current_content.append(line)
        
        # Save last article
        if in_article and current_title:
            articles.append({
                "title": current_title,
                "content": "\n".join(current_content).strip()
            })
            logger.debug(f"Found article: {current_title}")
        
        logger.info(f"Successfully split into {len(articles)} articles")
        return articles
    
    def save_articles(self, articles: List[Dict[str, str]]) -> None:
        """
        Save articles to individual files and metadata
        
        Args:
            articles: List of articles to save
        """
        # Create articles directory
        config.paths.articles_dir.mkdir(parents=True, exist_ok=True)
        
        metadata = []
        saved_count = 0
        
        logger.info(f"Saving {len(articles)} articles...")
        
        for art in articles:
            try:
                # Extract article number
                match = re.search(r"Điều\s+(\d+)", art['title'])
                num = match.group(1) if match else "000"
                safe_id = f"dieu_{int(num):03d}"
                filename = config.paths.articles_dir / f"{safe_id}.txt"
                
                # Save article content
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(art['content'])
                
                # Add to metadata
                metadata.append({
                    "id": safe_id,
                    "title": art['title'],
                    "file": str(filename.relative_to(config.paths.base_dir))
                })
                
                saved_count += 1
                logger.debug(f"Saved: {safe_id} - {art['title']}")
                
            except Exception as e:
                logger.error(f"Failed to save article '{art['title']}': {e}")
                continue
        
        # Save metadata
        try:
            with open(config.paths.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved metadata to {config.paths.metadata_path}")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise
        
        logger.info(f"Successfully saved {saved_count}/{len(articles)} articles")
    
    def process(self) -> int:
        """
        Main processing pipeline
        
        Returns:
            Number of articles processed
        """
        try:
            # Extract text
            text = self.extract_text()
            
            # Validate extraction
            if len(text) < 1000:
                logger.warning(f"Extracted text is suspiciously short: {len(text)} chars")
            
            # Split articles
            articles = self.split_articles(text)
            
            # Validate split
            if len(articles) == 0:
                logger.error("No articles found in PDF")
                return 0
            
            # Save articles
            self.save_articles(articles)
            
            return len(articles)
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise


def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info("PDF Splitter - Law Article Extraction")
        logger.info("=" * 60)
        
        # Initialize splitter
        splitter = PDFSplitter(config.paths.pdf_path)
        
        # Process PDF
        num_articles = splitter.process()
        
        logger.info("=" * 60)
        logger.info(f"✓ Successfully processed {num_articles} articles")
        logger.info("=" * 60)
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.error(f"Please place PDF at: {config.paths.pdf_path}")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())