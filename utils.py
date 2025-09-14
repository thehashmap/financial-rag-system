# utils.py - Common utilities and helper functions
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text from filings."""
    if not text:
        return ""

    # Remove multiple whitespaces
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters but keep financial notation
    text = re.sub(r'[^\w\s\.\,\$\%\(\)\-\:]', ' ', text)

    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def extract_financial_numbers(text: str) -> List[Dict[str, Any]]:
    """Extract financial numbers and percentages from text."""
    patterns = {
        'currency': r'\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion|thousand)?',
        'percentage': r'(\d+(?:\.\d+)?)\s*%',
        'revenue': r'revenue\s+(?:of\s+)?\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)',
        'margin': r'margin\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%'
    }

    findings = []
    for pattern_name, pattern in patterns.items():
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append({
                'type': pattern_name,
                'value': match.group(1),
                'context': text[max(0, match.start()-50):match.end()+50],
                'position': match.start()
            })

    return findings

def save_json(data: Any, filepath: Path) -> None:
    """Save data as JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved data to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")

def load_json(filepath: Path) -> Optional[Any]:
    """Load data from JSON file."""
    try:
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded data from {filepath}")
        return data
    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return None

def rate_limit_sleep(delay: float = 0.1) -> None:
    """Sleep to respect rate limits."""
    time.sleep(delay)

def get_filing_identifier(company: str, year: int) -> str:
    """Generate consistent filing identifier."""
    return f"{company}_{year}_10K"

def format_financial_response(
        query: str,
        answer: str,
        reasoning: str,
        sub_queries: List[str],
        sources: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Format response in the required JSON structure."""
    return {
        "query": query,
        "answer": answer,
        "reasoning": reasoning,
        "sub_queries": sub_queries,
        "sources": sources,
        "timestamp": datetime.now().isoformat()
    }

def create_source_reference(
        company: str,
        year: int,
        excerpt: str,
        page: Optional[int] = None,
        section: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized source reference."""
    return {
        "company": company,
        "year": year,
        "excerpt": excerpt[:200] + "..." if len(excerpt) > 200 else excerpt,
        "page": page,
        "section": section,
        "filing_type": "10-K"
    }

class ProgressTracker:
    """Simple progress tracking utility."""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description

    def update(self, increment: int = 1) -> None:
        self.current += increment
        progress = (self.current / self.total) * 100
        print(f"\r{self.description}: {self.current}/{self.total} ({progress:.1f}%)", end="", flush=True)

    def finish(self) -> None:
        print(f"\r{self.description}: Complete!")

def validate_environment() -> bool:
    """Validate that required environment is set up."""
    from config import DATA_DIR, OPENAI_API_KEY

    # Check directories
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        return False

    # Check API key (optional)
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not found. Will use open-source models.")

    logger.info("Environment validation passed")
    return True

if __name__ == "__main__":
    # Test utilities
    print("Testing utilities...")

    # Test text cleaning
    dirty_text = "  This   is   messy   text!!!  With  $1.2 million revenue  and 15.5% margin  "
    clean = clean_text(dirty_text)
    print(f"Cleaned: {clean}")

    # Test financial extraction
    numbers = extract_financial_numbers(clean)
    print(f"Financial numbers: {numbers}")

    # Test validation
    validate_environment()

    print("Utilities test completed")