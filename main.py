# main.py - Main CLI interface for the Financial RAG System
import sys
import json
from agent_system import SimpleFinancialAgent
from utils import logger

def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Financial RAG System - Usage:")
        print('python main.py "Your financial question here"')
        print("\nExample queries:")
        print('python main.py "What was Microsoft\'s total revenue in 2023?"')
        print('python main.py "Which company had the highest operating margin in 2023?"')
        print('python main.py "How did NVIDIA\'s data center revenue grow from 2022 to 2023?"')
        sys.exit(1)
    
    query = sys.argv[1]
    
    print(" Financial RAG System")
    print(f"Query: {query}")
    print("-" * 60)
    
    try:
        # Initialize agent
        agent = SimpleFinancialAgent()
        
        # Process query
        result = agent.answer_query(query)
        
        # Output formatted JSON result
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            "query": query,
            "error": str(e),
            "answer": "An error occurred while processing the query.",
            "reasoning": f"System error: {str(e)}",
            "sub_queries": [query],
            "sources": []
        }
        print(json.dumps(error_result, indent=2))
        logger.error(f"Error processing query '{query}': {e}")

if __name__ == "__main__":
    main()