# rag_pipeline.py - Simple RAG pipeline with embeddings
import json
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional
from config import RAW_FILINGS_DIR, PROCESSED_DATA_DIR, VECTOR_STORE_DIR, EMBEDDING_MODEL, TOP_K_RETRIEVAL
from utils import logger, load_json, save_json

class SimpleRAGPipeline:
    def __init__(self):
        self.model = None
        self.embeddings = None
        self.chunks = []
        self.embedding_cache_file = VECTOR_STORE_DIR / "embeddings.pkl"
        
    def load_processed_data(self) -> List[Dict]:
        """Load processed data from SEC-API or document processor."""
        # Try SEC-API data first
        api_data_file = RAW_FILINGS_DIR / "sec_api_data.json"
        processed_file = PROCESSED_DATA_DIR / "processed_documents.json"
        
        if api_data_file.exists():
            logger.info("Loading SEC-API data...")
            return self._convert_api_data_to_chunks(load_json(api_data_file))
        elif processed_file.exists():
            logger.info("Loading processed document data...")
            data = load_json(processed_file)
            # Flatten chunks from all documents
            all_chunks = []
            for doc in data:
                all_chunks.extend(doc['chunks'])
            return all_chunks
        else:
            logger.error("No processed data found. Run data acquisition first.")
            return []
    
    def _convert_api_data_to_chunks(self, api_data: List[Dict]) -> List[Dict]:
        """Convert SEC-API data to chunks format."""
        chunks = []
        chunk_id = 0
        
        for filing in api_data:
            company = filing['company']
            year = filing['year']
            
            for section_name, section_data in filing['sections'].items():
                content = section_data['content']
                
                # Simple chunking - split by paragraphs and sentences
                text_chunks = self._simple_chunk_text(content)
                
                for i, chunk_text in enumerate(text_chunks):
                    chunks.append({
                        'text': chunk_text,
                        'company': company,
                        'year': year,
                        'section': section_name,
                        'chunk_id': f"{company}_{year}_{section_name}_{i}",
                        'source_file': f"{company}_{year}_api_data",
                        'filing_url': filing.get('filing_url', '')
                    })
                    chunk_id += 1
        
        logger.info(f"Created {len(chunks)} chunks from {len(api_data)} filings")
        return chunks
    
    def _simple_chunk_text(self, text: str, max_words: int = 300, overlap: int = 50) -> List[str]:
        """Simple word-based chunking."""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + max_words]
            chunk = ' '.join(chunk_words)
            
            # Only keep substantial chunks
            if len(chunk.strip()) > 100:
                chunks.append(chunk)
            
            i += max_words - overlap
        
        return chunks
    
    def build_embeddings(self, force_rebuild: bool = False):
        """Build or load embeddings for all chunks."""
        # Check if cached embeddings exist
        if self.embedding_cache_file.exists() and not force_rebuild:
            logger.info("Loading cached embeddings...")
            with open(self.embedding_cache_file, 'rb') as f:
                cached_data = pickle.load(f)
                self.model = cached_data['model']
                self.embeddings = cached_data['embeddings']
                self.chunks = cached_data['chunks']
            logger.info(f"Loaded {len(self.chunks)} chunks with embeddings")
            return
        
        # Load data and build embeddings
        logger.info("Building embeddings from scratch...")
        self.chunks = self.load_processed_data()
        
        if not self.chunks:
            logger.error("No chunks to process")
            return
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Extract text for embedding
        chunk_texts = [chunk['text'] for chunk in self.chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
        self.embeddings = self.model.encode(
            chunk_texts, 
            normalize_embeddings=True,
            show_progress_bar=True
        )
        
        # Cache embeddings
        cache_data = {
            'model': self.model,
            'embeddings': self.embeddings,
            'chunks': self.chunks
        }
        
        with open(self.embedding_cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        logger.info(f"Cached embeddings for {len(self.chunks)} chunks")
    
    def search(self, query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict[str, Any]]:
        """Search for relevant chunks using cosine similarity."""
        if self.model is None or self.embeddings is None:
            logger.error("Embeddings not built. Call build_embeddings() first.")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], normalize_embeddings=True)
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Get top-k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Return results with metadata
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx].copy()
            chunk['similarity_score'] = float(similarities[idx])
            results.append(chunk)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        if not self.chunks:
            return {"error": "No data loaded"}
        
        companies = set(chunk['company'] for chunk in self.chunks)
        years = set(str(chunk['year']) for chunk in self.chunks)
        sections = set(chunk['section'] for chunk in self.chunks)
        
        return {
            "total_chunks": len(self.chunks),
            "companies": sorted(companies),
            "years": sorted(years),
            "sections": sorted(sections),
            "embedding_model": EMBEDDING_MODEL,
            "cache_exists": self.embedding_cache_file.exists()
        }

def main():
    """Test the RAG pipeline."""
    print(" Testing RAG Pipeline...")
    
    rag = SimpleRAGPipeline()
    
    # Build embeddings
    rag.build_embeddings()
    
    # Show stats
    stats = rag.get_stats()
    print(f" Pipeline ready with {stats['total_chunks']} chunks")
    print(f"  Companies: {stats['companies']}")
    print(f"  Years: {stats['years']}")
    print(f"  Sections: {stats['sections']}")
    
    # Test searches
    test_queries = [
        "What was Microsoft's total revenue in 2023?",
        "NVIDIA data center revenue",
        "Google cloud revenue growth",
        "AI investments and strategy"
    ]
    
    print("\n🔍 Testing searches:")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = rag.search(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['company']} {result['year']} ({result['section']}) - Score: {result['similarity_score']:.3f}")
            print(f"     {result['text'][:100]}...")

if __name__ == "__main__":
    main()