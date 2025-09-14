# agent_system.py - Simple agent for query decomposition and synthesis
import re
from typing import List, Dict, Any
from rag_pipeline import SimpleRAGPipeline
from utils import format_financial_response, create_source_reference, logger

class SimpleFinancialAgent:
    def __init__(self):
        self.rag = SimpleRAGPipeline()
        self.rag.build_embeddings()
        
        # Simple patterns for query classification
        self.comparative_patterns = [
            r'compar\w+',
            r'vs\.?|versus',
            r'which.*highest|which.*lowest|which.*best',
            r'growth.*from.*to',
            r'all three companies',
            r'across.*companies'
        ]
        
        self.multi_year_patterns = [
            r'\d{4}.*to.*\d{4}',
            r'from.*\d{4}.*to.*\d{4}',
            r'growth.*\d{4}.*\d{4}'
        ]
    
    def classify_query(self, query: str) -> str:
        """Classify query type for decomposition strategy."""
        query_lower = query.lower()
        
        # Check for comparative queries
        for pattern in self.comparative_patterns:
            if re.search(pattern, query_lower):
                return "comparative"
        
        # Check for multi-year queries
        for pattern in self.multi_year_patterns:
            if re.search(pattern, query_lower):
                return "multi_year"
        
        return "simple"
    
    def decompose_query(self, query: str) -> List[str]:
        """Decompose complex queries into simpler sub-queries."""
        query_type = self.classify_query(query)
        
        if query_type == "simple":
            return [query]
        
        elif query_type == "comparative":
            # For comparative queries, create sub-queries for each company
            companies = ["Microsoft", "Google", "NVIDIA"]
            
            # Extract the metric/topic from the query
            sub_queries = []
            for company in companies:
                # Simple substitution approach
                modified_query = query.replace("which company", company)
                modified_query = modified_query.replace("all three companies", company)
                modified_query = modified_query.replace("companies", company)
                sub_queries.append(modified_query)
            
            return sub_queries
        
        elif query_type == "multi_year":
            # For multi-year queries, create sub-queries for each year
            years = re.findall(r'\b(20\d{2})\b', query)
            if len(years) >= 2:
                sub_queries = []
                for year in years:
                    year_query = re.sub(r'from.*to.*\d{4}', f'in {year}', query)
                    year_query = re.sub(r'\d{4}.*to.*\d{4}', year, year_query)
                    sub_queries.append(year_query)
                return sub_queries
        
        return [query]  # Fallback
    
    def search_and_extract_info(self, query: str) -> Dict[str, Any]:
        """Search for information and extract key details."""
        results = self.rag.search(query, top_k=3)
        
        if not results:
            return {"found": False, "answer": "No relevant information found"}
        
        # Combine top results
        combined_text = " ".join([r['text'] for r in results[:2]])
        
        # Simple information extraction
        answer = self._extract_answer(query, combined_text, results)
        
        return {
            "found": True,
            "answer": answer,
            "results": results,
            "source_chunks": len(results)
        }
    
    def _extract_answer(self, query: str, text: str, results: List[Dict]) -> str:
        """Simple answer extraction from text."""
        # For this simple implementation, just return the most relevant chunk
        if results:
            best_chunk = results[0]
            # Try to find sentences that might contain the answer
            sentences = text.split('.')
            
            # Look for sentences with numbers (likely contain financial data)
            financial_sentences = []
            for sentence in sentences:
                if re.search(r'\$[\d,]+|[\d.]+%|revenue|income|margin', sentence, re.IGNORECASE):
                    financial_sentences.append(sentence.strip())
            
            if financial_sentences:
                return '. '.join(financial_sentences[:2]) + '.'
            else:
                # Fallback to first chunk
                return best_chunk['text'][:300] + "..."
        
        return "Information not found in the available documents."
    
    def synthesize_results(self, query: str, sub_results: List[Dict]) -> str:
        """Synthesize results from multiple sub-queries."""
        if len(sub_results) == 1:
            return sub_results[0]['answer']
        
        # For comparative queries, try to synthesize
        if self.classify_query(query) == "comparative":
            synthesis = "Based on the filings analysis:\n\n"
            for i, result in enumerate(sub_results):
                if result['found']:
                    synthesis += f"• {result['answer']}\n"
            
            # Try to determine winner for "which company" questions
            if "which company" in query.lower() and "highest" in query.lower():
                synthesis += "\nBased on the available data, specific comparison requires detailed financial analysis."
            
            return synthesis
        
        # For multi-year queries
        elif "growth" in query.lower():
            return f"Growth analysis: {sub_results[0]['answer']} compared to {sub_results[1]['answer']}"
        
        # Default synthesis
        return "; ".join([r['answer'] for r in sub_results if r['found']])
    
    def answer_query(self, query: str) -> Dict[str, Any]:
        """Main method to answer any query with agent capabilities."""
        logger.info(f"Processing query: {query}")
        
        # Decompose query
        sub_queries = self.decompose_query(query)
        logger.info(f"Decomposed into {len(sub_queries)} sub-queries")
        
        # Process each sub-query
        sub_results = []
        for sub_query in sub_queries:
            result = self.search_and_extract_info(sub_query)
            sub_results.append(result)
        
        # Synthesize answer
        final_answer = self.synthesize_results(query, sub_results)
        
        # Create sources from all results
        all_sources = []
        for result in sub_results:
            if result['found']:
                for chunk in result['results'][:2]:  # Top 2 per sub-query
                    source = create_source_reference(
                        chunk['company'],
                        chunk['year'],
                        chunk['text'][:200],
                        section=chunk['section']
                    )
                    all_sources.append(source)
        
        # Remove duplicate sources
        unique_sources = []
        seen_sources = set()
        for source in all_sources:
            key = (source['company'], source['year'], source['section'])
            if key not in seen_sources:
                unique_sources.append(source)
                seen_sources.add(key)
        
        # Create reasoning
        reasoning = f"Processed {len(sub_queries)} sub-queries and retrieved information from {len(unique_sources)} sources across the filings."
        
        return format_financial_response(
            query=query,
            answer=final_answer,
            reasoning=reasoning,
            sub_queries=sub_queries,
            sources=unique_sources[:5]  # Limit to top 5 sources
        )

def main():
    """Test the agent system."""
    print(" Testing Agent System...")
    
    agent = SimpleFinancialAgent()
    
    # Test queries
    test_queries = [
        "What was Microsoft's total revenue in 2023?",
        "Which company had the highest operating margin in 2023?",
        "How did NVIDIA's data center revenue grow from 2022 to 2023?",
        "Compare AI investments mentioned by all three companies"
    ]
    
    for query in test_queries:
        print(f"\n" + "="*60)
        print(f"Query: {query}")
        print("="*60)
        
        result = agent.answer_query(query)
        
        print(f"Answer: {result['answer'][:200]}...")
        print(f"Sub-queries: {len(result['sub_queries'])}")
        print(f"Sources: {len(result['sources'])}")

if __name__ == "__main__":
    main()