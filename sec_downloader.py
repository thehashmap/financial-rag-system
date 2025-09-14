# sec_api_downloader.py - Complete SEC-API.io integration for reliable filing extraction
import requests
import time
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from config import COMPANIES, YEARS, RAW_FILINGS_DIR
from utils import logger, save_json


class SECAPIDownloader:
    def __init__(self):
        """Initialize SEC API downloader with API key from environment."""
        self.api_key = os.getenv('SEC_API_KEY')
        if not self.api_key:
            raise ValueError(
                "SEC_API_KEY environment variable not set. "
                "Get your API key from https://sec-api.io/ and set it in your .env file"
            )

        self.query_url = "https://api.sec-api.io"
        self.extractor_url = "https://api.sec-api.io/extractor"
        self.session = requests.Session()
        self.session.headers.update({'Authorization': self.api_key})

        # Cache for filing URLs to avoid duplicate API calls
        self.filing_cache = {}

    def search_filings(self, company_cik: str, form_type: str = "10-K",
                       year: Optional[int] = None, limit: int = 10) -> List[Dict]:
        """Search for filings using SEC-API Query API."""
        # Construct search query
        query_parts = [
            f'cik:{company_cik}',
            f'formType:"{form_type}"'
        ]

        # Add date filter if year is specified
        if year:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            query_parts.append(f'filedAt:[{start_date} TO {end_date}]')

        query_string = " AND ".join(query_parts)

        payload = {
            "query": query_string,
            "from": "0",
            "size": str(limit),
            "sort": [{"filedAt": {"order": "desc"}}]
        }

        try:
            logger.info(f"Searching filings: {query_string}")
            response = self.session.post(self.query_url, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            filings = data.get('filings', [])

            logger.info(f"Found {len(filings)} filings for CIK {company_cik} in {year}")
            return filings

        except Exception as e:
            logger.error(f"Error searching filings for CIK {company_cik}: {e}")
            return []

    def get_filing_url(self, company: str, year: int) -> Optional[str]:
        """Get the most recent 10-K filing URL for a company and year."""
        cache_key = f"{company}_{year}"

        if cache_key in self.filing_cache:
            return self.filing_cache[cache_key]

        company_cik = COMPANIES[company]
        filings = self.search_filings(company_cik, "10-K", year, 5)

        # Find the best matching filing
        for filing in filings:
            filing_year = datetime.fromisoformat(
                filing['filedAt'].replace('Z', '+00:00')
            ).year

            # For fiscal year filings, check both filing year and period year
            period_year = None
            if filing.get('periodOfReport'):
                period_year = datetime.fromisoformat(
                    filing['periodOfReport']
                ).year

            # Match by either filing year or period year
            if filing_year == year or period_year == year:
                url = filing.get('linkToFilingDetails')
                if url:
                    self.filing_cache[cache_key] = url
                    logger.info(f"Found {company} {year} filing: {url}")
                    return url

        logger.warning(f"No {year} 10-K filing found for {company}")
        return None

    def extract_section(self, filing_url: str, item: str,
                        return_type: str = 'text') -> Optional[str]:
        """Extract a specific section from a filing using SEC-API Extractor."""
        params = {
            'url': filing_url,
            'item': item,
            'type': return_type,
            'token': self.api_key
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    self.extractor_url,
                    params=params,
                    timeout=60
                )
                response.raise_for_status()

                content = response.text

                # Check for "processing" response
                if content.strip().lower() == "processing":
                    if attempt < max_retries - 1:
                        logger.info(f"Processing... retrying in 1 second (attempt {attempt + 1})")
                        time.sleep(1)
                        continue
                    else:
                        logger.warning(f"Section {item} still processing after {max_retries} attempts")
                        return None

                # Check for empty or error responses
                if not content or len(content.strip()) < 10:
                    logger.warning(f"Empty or minimal content for item {item}")
                    return None

                return content

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error extracting item {item}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
            except Exception as e:
                logger.error(f"Unexpected error extracting item {item}: {e}")
                return None

        return None

    def download_company_data(self, company: str, year: int) -> Optional[Dict]:
        """Download key sections for a company and year."""
        logger.info(f"Processing {company} {year}...")

        filing_url = self.get_filing_url(company, year)
        if not filing_url:
            return None

        # Extract key sections relevant for financial Q&A
        sections_config = {
            'business': {
                'item': '1',
                'description': 'Business Description'
            },
            'risk_factors': {
                'item': '1A',
                'description': 'Risk Factors'
            },
            'financial_performance': {
                'item': '7',
                'description': "Management's Discussion and Analysis"
            },
            'financial_statements': {
                'item': '8',
                'description': 'Financial Statements'
            }
        }

        company_data = {
            'company': company,
            'year': year,
            'filing_url': filing_url,
            'sections': {},
            'extraction_timestamp': datetime.now().isoformat(),
            'cik': COMPANIES[company]
        }

        sections_extracted = 0

        for section_name, config in sections_config.items():
            item_code = config['item']
            description = config['description']

            logger.info(f"  Extracting {description} (Item {item_code})...")

            content = self.extract_section(filing_url, item_code, 'text')

            if content and len(content.strip()) > 100:  # Reasonable minimum length
                # Limit content size but keep meaningful amount
                max_chars = 50000  # 50K chars should be plenty for chunking
                truncated_content = content[:max_chars]

                company_data['sections'][section_name] = {
                    'item': item_code,
                    'description': description,
                    'content': truncated_content,
                    'full_length': len(content),
                    'truncated': len(content) > max_chars
                }

                sections_extracted += 1
                logger.info(f"     Extracted {len(content):,} characters")

                if len(content) > max_chars:
                    logger.info(f"    ℹ Truncated to {max_chars:,} characters")
            else:
                logger.warning(f"     Failed to extract {description}")

            # Rate limiting to be respectful to the API
            time.sleep(0.5)

        if sections_extracted > 0:
            logger.info(f"  Successfully extracted {sections_extracted}/{len(sections_config)} sections")
            return company_data
        else:
            logger.error(f"  No sections successfully extracted for {company} {year}")
            return None

    def download_all_data(self) -> List[Dict]:
        """Download data for all companies and years."""
        logger.info("Starting comprehensive SEC filing download...")
        logger.info(f"Target: {len(COMPANIES)} companies × {len(YEARS)} years = {len(COMPANIES) * len(YEARS)} filings")

        all_data = []
        successful_downloads = 0
        failed_downloads = []

        for company in COMPANIES.keys():
            for year in YEARS:
                try:
                    data = self.download_company_data(company, year)
                    if data:
                        all_data.append(data)
                        successful_downloads += 1
                    else:
                        failed_downloads.append(f"{company} {year}")

                except Exception as e:
                    logger.error(f"Failed to process {company} {year}: {e}")
                    failed_downloads.append(f"{company} {year}")

                # Brief pause between companies to be respectful
                time.sleep(1)

        # Save all data
        if all_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = RAW_FILINGS_DIR / f"sec_api_data_{timestamp}.json"
            save_json(all_data, output_file)

            # Also save the latest version
            latest_file = RAW_FILINGS_DIR / "sec_api_data_latest.json"
            save_json(all_data, latest_file)

        # Print summary
        logger.info(f"\n{'=' * 60}")
        logger.info("DOWNLOAD SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(f"Successful downloads: {successful_downloads}")
        logger.info(f"Failed downloads: {len(failed_downloads)}")

        if failed_downloads:
            logger.warning("Failed downloads:")
            for item in failed_downloads:
                logger.warning(f"  - {item}")

        if all_data:
            logger.info(f"\nData saved to: {RAW_FILINGS_DIR}")

            # Show what we extracted
            logger.info("\nExtracted data summary:")
            for item in all_data:
                sections = list(item['sections'].keys())
                logger.info(f"  {item['company']} {item['year']}: {len(sections)} sections")

        return all_data

    def verify_api_access(self) -> bool:
        """Verify API access by making a simple test query."""
        test_payload = {
            "query": "ticker:AAPL AND formType:\"10-K\"",
            "from": "0",
            "size": "1"
        }

        try:
            response = self.session.post(self.query_url, json=test_payload, timeout=10)
            response.raise_for_status()

            data = response.json()
            if 'filings' in data and isinstance(data['filings'], list):
                logger.info(" SEC-API access verified successfully")
                return True
            else:
                logger.error(" Invalid response format from SEC-API")
                return False

        except Exception as e:
            logger.error(f" SEC-API access verification failed: {e}")
            return False


def main():
    """Main function to run the downloader."""
    print("SEC Filing Downloader")
    print("=" * 50)

    try:
        # Initialize downloader
        downloader = SECAPIDownloader()

        # Verify API access
        if not downloader.verify_api_access():
            print("\nFailed to verify API access. Please check:")
            print("1. Your SEC_API_KEY environment variable is set")
            print("2. Your API key is valid and has quota remaining")
            print("3. Your internet connection is working")
            return

        # Download all data
        print("\nStarting download process...")
        data = downloader.download_all_data()

        if data:
            print(f"\n SUCCESS: Downloaded data for {len(data)} company/year combinations")
            print("\nNext steps:")
            print("1. Run the document processor to chunk the text")
            print("2. Generate embeddings for the chunks")
            print("3. Set up the RAG query system")
        else:
            print("\n No data was successfully downloaded")
            print("Check the logs for specific error details")

    except ValueError as e:
        print(f"\n Configuration Error: {e}")
        print("\nTo fix this:")
        print("1. Get an API key from https://sec-api.io/")
        print("2. Add SEC_API_KEY=your_api_key to your .env file")
        print("3. Or set the environment variable: export SEC_API_KEY=your_api_key")

    except Exception as e:
        print(f"\n Unexpected Error: {e}")
        logger.error(f"Unexpected error in main: {e}")


if __name__ == "__main__":
    main()