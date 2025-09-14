# config.py - Configuration and constants for Financial RAG System
import os
from pathlib import Path
from typing import Dict, List

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not installed, will rely on system environment variables
    pass

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_FILINGS_DIR = DATA_DIR / "raw_filings"
PROCESSED_DIR = DATA_DIR / "processed"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"

# Create directories if they don't exist
for dir_path in [DATA_DIR, RAW_FILINGS_DIR, PROCESSED_DIR, VECTOR_STORE_DIR]:
    dir_path.mkdir(exist_ok=True)

# Company information with CIK codes for SEC API
COMPANIES: Dict[str, str] = {
    'GOOGL': '1652044',  # Alphabet Inc.
    'MSFT': '789019',  # Microsoft Corporation
    'NVDA': '1045810'  # NVIDIA Corporation
}

# Years to fetch (2022, 2023, 2024)
YEARS: List[int] = [2022, 2023, 2024]

# SEC-API configuration
SEC_API_KEY = os.getenv('SEC_API_KEY')
SEC_API_BASE_URL = "https://api.sec-api.io"

# RAG Configuration
CHUNK_SIZE = 500  # Number of words per chunk
CHUNK_OVERLAP = 50  # Word overlap between chunks
MAX_CHUNKS_PER_QUERY = 10  # Maximum chunks to retrieve per query

# Embedding configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Fast, good quality model
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2

# LLM Configuration (prioritize free/open-source options)
LLM_CONFIG = {
    'groq': {
        'api_key': os.getenv('GROQ_API_KEY'),
        'model': 'mixtral-8x7b-32768',
        'base_url': 'https://api.groq.com/openai/v1'
    },
    'openai': {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': 'gpt-3.5-turbo',
        'base_url': 'https://api.openai.com/v1'
    },
    'gemini': {
        'api_key': os.getenv('GEMINI_API_KEY'),
        'model': 'gemini-1.5-flash'
    }
}

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "rag_system.log"

# Query types for testing
SAMPLE_QUERIES = [
    # Simple queries
    "What was NVIDIA's total revenue in fiscal year 2024?",
    "What percentage of Google's 2023 revenue came from advertising?",

    # Comparative queries (require agent decomposition)
    "How much did Microsoft's cloud revenue grow from 2022 to 2023?",
    "Which of the three companies had the highest gross margin in 2023?",

    # Complex multi-step queries
    "Compare the R&D spending as a percentage of revenue across all three companies in 2023",
    "How did each company's operating margin change from 2022 to 2024?",
    "What are the main AI risks mentioned by each company and how do they differ?"
]

# System prompts for agent orchestration
SYSTEM_PROMPTS = {
    'query_decomposer': """
You are a financial query decomposition agent. Your job is to break down complex questions into simpler sub-queries that can be answered by searching through SEC filings.

For simple questions about a single company and metric, return the original query.
For comparative questions, create sub-queries for each company or time period being compared.
For complex questions, break them into logical steps.

Return your analysis as JSON with this format:
{
    "is_complex": boolean,
    "sub_queries": [list of sub-queries],
    "synthesis_strategy": "description of how to combine answers"
}
""",

    'answer_synthesizer': """
You are a financial answer synthesis agent. You combine information from multiple document searches to provide comprehensive, accurate answers to financial questions.

Always:
- Provide specific numbers with proper context
- Cite the company and year for each data point  
- Calculate growth rates and comparisons when requested
- Indicate if any requested information is missing
- Format financial numbers clearly (e.g., $1.2 billion, 15.3%)
"""
}


def validate_environment() -> Dict[str, bool]:
    """Validate required environment variables and dependencies."""
    validation_results = {}

    # Check SEC API key
    validation_results['SEC_API_KEY'] = bool(SEC_API_KEY)

    # Check optional LLM API keys
    validation_results['has_llm_key'] = any([
        LLM_CONFIG['groq']['api_key'],
        LLM_CONFIG['openai']['api_key'],
        LLM_CONFIG['gemini']['api_key']
    ])

    # Check data directories
    validation_results['data_directories'] = all([
        path.exists() for path in [DATA_DIR, RAW_FILINGS_DIR, PROCESSED_DIR, VECTOR_STORE_DIR]
    ])

    return validation_results


def print_config_summary():
    """Print configuration summary for debugging."""
    print("Financial RAG System Configuration")
    print("=" * 50)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Companies: {list(COMPANIES.keys())}")
    print(f"Years: {YEARS}")
    print(f"Chunk Size: {CHUNK_SIZE} words")
    print(f"Embedding Model: {EMBEDDING_MODEL}")

    validation = validate_environment()
    print("\nEnvironment Validation:")
    for key, status in validation.items():
        status_icon = "✓" if status else "✗"
        print(f"  {status_icon} {key}: {status}")

    if not validation['SEC_API_KEY']:
        print("\n⚠️  SEC_API_KEY not found. Please set it in your .env file or environment.")
        print("   Get your API key from: https://sec-api.io/")

    if not validation['has_llm_key']:
        print("\n⚠️  No LLM API keys found. You can:")
        print("   - Set GROQ_API_KEY (recommended - free tier available)")
        print("   - Set OPENAI_API_KEY")
        print("   - Set GEMINI_API_KEY")
        print("   - Or use local models (to be implemented)")


if __name__ == "__main__":
    print_config_summary()