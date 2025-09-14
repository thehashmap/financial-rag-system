# Financial RAG System with Agent Capabilities

A focused RAG system with basic agent capabilities for answering financial questions about Google, Microsoft, and NVIDIA using their 10-K filings.

## 🚀 Project Status: Updated SEC Downloader Complete

### What's Working Now:
- ✅ Project structure and configuration
- ✅ Environment variable management
- ✅ **Dynamic SEC filing discovery and download**
- ✅ **Comprehensive error handling and retry logic**
- ✅ **Support for all required company/year combinations**

### What's Next:
- 🔄 Document processing and text extraction
- ⏳ RAG pipeline implementation  
- ⏳ Agent orchestration system

## 📁 Project Structure

```
financial-rag-system/
├── config.py                   # Configuration with environment variables
├── sec_api_downloader.py      # Dynamic SEC filing downloader
├── utils.py                   # Common utilities  
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── data/                     # Data storage
│   ├── raw_filings/         # Original SEC filings
│   ├── processed/           # Processed documents
│   └── vector_store/        # Vector embeddings
└── rag_system.log           # Application logs
```

## 🛠 Setup Instructions

### 1. Environment Setup

```bash
# Clone and create virtual environment
git clone <your-repo>
cd financial-rag-system
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. API Keys Configuration

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required: SEC-API.io API Key
SEC_API_KEY=your_sec_api_key_here

# At least one LLM API key (choose one):
GROQ_API_KEY=your_groq_api_key_here        # Recommended: fast + free tier
OPENAI_API_KEY=your_openai_api_key_here    # Requires paid account
GEMINI_API_KEY=your_gemini_api_key_here    # Free tier available
```

**Where to get API keys:**
- **SEC-API.io**: [https://sec-api.io/](https://sec-api.io/) - Free tier available
- **Groq** (Recommended): [https://console.groq.com/](https://console.groq.com/) - Fast inference, generous free tier
- **OpenAI**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) - Requires paid account
- **Google Gemini**: [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) - Free tier available

### 3. Test Your Setup

```bash
# Validate configuration
python config.py

# Download SEC filings
python sec_api_downloader.py
```

## 📊 Data Coverage

The system downloads 10-K filings for:

| Company | Ticker | CIK | Years |
|---------|---------|------|-------|
| Google/Alphabet | GOOGL | 1652044 | 2022, 2023, 2024 |
| Microsoft | MSFT | 789019 | 2022, 2023, 2024 |
| NVIDIA | NVDA | 1045810 | 2022, 2023, 2024 |

**Total**: 9 filings with key sections extracted:
- Item 1: Business Description
- Item 1A: Risk Factors  
- Item 7: Management's Discussion & Analysis
- Item 8: Financial Statements

## 🎯 Target Capabilities (Final System)

The system will support these query types:

1. **Basic Metrics:** "What was Microsoft's total revenue in 2023?"
2. **YoY Comparison:** "How did NVIDIA's data center revenue grow from 2022 to 2023?"
3. **Cross-Company:** "Which company had the highest operating margin in 2023?"
4. **Segment Analysis:** "What percentage of Google's revenue came from cloud in 2023?"
5. **AI Strategy:** "Compare AI investments mentioned by all three companies in their 2024 10-Ks"

## 🔧 New Features in SEC Downloader

### Dynamic Filing Discovery
- Uses SEC-API Query API to find filings programmatically
- No hardcoded URLs - automatically finds the most recent 10-K for each year
- Handles different fiscal year patterns across companies

### Robust Error Handling
- Automatic retries for "processing" responses
- Rate limiting to respect API quotas
- Comprehensive logging and progress tracking
- Graceful handling of missing filings

### Smart Content Extraction
- Extracts 4 key sections from each filing
- Intelligent content truncation (50K chars per section)
- Caches filing URLs to avoid duplicate API calls
- Detailed extraction summaries

### Usage Example

```python
from sec_api_downloader import SECAPIDownloader

# Initialize downloader (reads SEC_API_KEY from environment)
downloader = SECAPIDownloader()

# Download all filings
data = downloader.download_all_data()

# Or download specific company/year
single_filing = downloader.download_company_data('NVDA', 2024)
```

## 🏗 Architecture Overview

- **Data Layer:** Dynamic SEC filing discovery and extraction
- **RAG Layer:** Chunking, embeddings, and vector retrieval
- **Agent Layer:** Query decomposition and multi-step reasoning
- **Interface:** CLI for query processing

## 🔧 Development Progress

### ✅ Commit 1: Foundation
- Project structure and configuration
- Utility functions and helpers
- Environment setup and validation

### ✅ Commit 2: Enhanced Data Acquisition  
- **Dynamic SEC filing discovery** using Query API
- **Intelligent content extraction** with retry logic
- **Comprehensive error handling** and logging
- **Environment variable management** for API keys
- **Support for all 9 required filings** (3 companies × 3 years)

### 🔄 Commit 3: RAG Pipeline (Next)
- Embedding generation using sentence-transformers
- Vector storage with FAISS
- Basic retrieval functionality
- Document chunking and preprocessing

### ⏳ Commit 4: Agent System
- Query decomposition logic
- Multi-step reasoning
- Result synthesis
- CLI interface

## 🚨 Troubleshooting

### SEC API Issues
```bash
# If you get "No filing found" errors:
python -c "
from sec_api_downloader import SECAPIDownloader
d = SECAPIDownloader()
print('API Access:', d.verify_api_access())
"
```

### Common Error Solutions

**"SEC_API_KEY environment variable not set"**
- Copy `.env.example` to `.env`
- Add your SEC-API.io API key to the `.env` file
- Make sure `.env` is in the project root directory

**"No 2024 10-K filing found for GOOGL"**
- Some 2024 filings may not be available yet
- The system will skip missing filings and continue
- Check the logs for specific details

**"Processing... retrying" messages**
- This is normal - SEC-API processes filings on-demand
- The system automatically retries with delays
- Usually resolves within 1-3 attempts

## 📝 Sample Output

When you run `python sec_api_downloader.py`, you should see:

```
SEC Filing Downloader
==================================================
✓ SEC-API access verified successfully

Starting comprehensive SEC filing download...
Target: 3 companies × 3 years = 9 filings

Processing GOOGL 2022...
Found GOOGL 2022 filing: https://www.sec.gov/Archives/edgar/...
  Extracting Business Description (Item 1)...
    ✓ Extracted 45,234 characters
  Extracting Risk Factors (Item 1A)...
    ✓ Extracted 52,891 characters
  ...
  Successfully extracted 4/4 sections

============================================================
DOWNLOAD SUMMARY
============================================================
Successful downloads: 8
Failed downloads: 1
Failed downloads:
  - NVDA 2024

Data saved to: data/raw_filings/
```

## 🧪 Testing Your Installation

```bash
# Test 1: Check configuration
python config.py

# Test 2: Test SEC API access
python -c "
from sec_api_downloader import SECAPIDownloader
d = SECAPIDownloader()
d.verify_api_access()
"

# Test 3: Download a single filing
python -c "
from sec_api_downloader import SECAPIDownloader
d = SECAPIDownloader()
data = d.download_company_data('MSFT', 2023)
print('Success!' if data else 'Failed!')
"

# Test 4: Full download
python sec_api_downloader.py
```

## 📚 Next Steps

After successful data acquisition:

1. **Document Processing**: Implement text chunking and preprocessing
2. **Embedding Generation**: Create vector representations of text chunks
3. **Vector Storage**: Set up FAISS or ChromaDB for similarity search
4. **Query Engine**: Build the agent system for query decomposition
5. **CLI Interface**: Create the final query interface

## 🤝 Contributing

This is a sprint challenge implementation focusing on:
- Clean, practical solutions
- RAG fundamentals demonstration  
- Agent orchestration capabilities
- Professional code structure

## 📄 License

This project is for educational and demonstration purposes.