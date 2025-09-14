# document_processor.py - Simple document processing
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict
from config import RAW_FILINGS_DIR, PROCESSED_DATA_DIR, CHUNK_SIZE
from utils import clean_text, save_json, logger

class DocumentProcessor:
    def __init__(self):
        self.processed_docs = []
    
    def extract_text_from_html(self, filepath: Path) -> str:
        """Extract clean text from HTML filing."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it
            text = soup.get_text()
            text = clean_text(text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            return ""
    
    def simple_chunk_text(self, text: str, max_words: int = CHUNK_SIZE) -> List[str]:
        """Simple word-based chunking."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), max_words):
            chunk_words = words[i:i + max_words]
            chunk = ' '.join(chunk_words)
            
            # Only keep substantial chunks
            if len(chunk.strip()) > 100:
                chunks.append(chunk)
        
        return chunks
    
    def extract_key_sections(self, text: str) -> Dict[str, str]:
        """Extract key sections from 10-K filing."""
        sections = {}
        
        # Common 10-K section patterns
        section_patterns = {
            'business': r'item\s+1[\.\s]*business',
            'risk_factors': r'item\s+1a[\.\s]*risk\s+factors',
            'financial_performance': r'item\s+7[\.\s]*management.*discussion',
            'financial_statements': r'item\s+8[\.\s]*financial\s+statements'
        }
        
        for section_name, pattern in section_patterns.items():
            # Find section start
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_pos = match.start()
                # Get next ~5000 chars as a reasonable section size
                section_text = text[start_pos:start_pos + 5000]
                sections[section_name] = clean_text(section_text)
        
        # If no sections found, just use the full text
        if not sections:
            sections['full_document'] = text[:10000]  # First 10k chars
        
        return sections
    
    def process_filing(self, filepath: Path) -> Dict:
        """Process a single filing."""
        # Extract company and year from filename
        filename = filepath.stem  # Remove extension
        parts = filename.split('_')
        company = parts[0]
        year = int(parts[1])
        
        logger.info(f"Processing {company} {year}...")
        
        # Extract text
        text = self.extract_text_from_html(filepath)
        if not text:
            return None
        
        # Extract sections
        sections = self.extract_key_sections(text)
        
        # Create chunks for each section
        all_chunks = []
        for section_name, section_text in sections.items():
            chunks = self.simple_chunk_text(section_text)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    'text': chunk,
                    'company': company,
                    'year': year,
                    'section': section_name,
                    'chunk_id': f"{company}_{year}_{section_name}_{i}",
                    'source_file': filename
                })
        
        doc_info = {
            'company': company,
            'year': year,
            'filename': filename,
            'total_chunks': len(all_chunks),
            'sections': list(sections.keys()),
            'chunks': all_chunks
        }
        
        return doc_info
    
    def process_all_filings(self):
        """Process all downloaded filings."""
        html_files = list(RAW_FILINGS_DIR.glob("*.html"))
        
        if not html_files:
            logger.warning("No HTML files found to process")
            return
        
        processed_docs = []
        total_chunks = 0
        
        for filepath in sorted(html_files):
            doc_info = self.process_filing(filepath)
            if doc_info:
                processed_docs.append(doc_info)
                total_chunks += doc_info['total_chunks']
        
        # Save processed data
        output_file = PROCESSED_DATA_DIR / "processed_documents.json"
        save_json(processed_docs, output_file)
        
        logger.info(f"✓ Processed {len(processed_docs)} documents with {total_chunks} total chunks")
        return processed_docs

def main():
    """Main function to process all filings."""
    print("Processing documents...")
    
    processor = DocumentProcessor()
    docs = processor.process_all_filings()
    
    if docs:
        print(f"✓ Processing complete: {len(docs)} documents")
        for doc in docs:
            print(f"  - {doc['company']} {doc['year']}: {doc['total_chunks']} chunks")
    else:
        print("No documents processed")

if __name__ == "__main__":
    main()