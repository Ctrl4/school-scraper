# School Data Scraper

A modular web scraping framework for collecting and enriching school data from various state education portals.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Chrome browser
- Pyenv (Optional Recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ctrl4th/school-scraper.git
cd school-scraper
```

2. Create and activate a virtual environment (if you have pyenv):
```bash
pyenv virtualenv 3.11 school-scraper-env
pyenv shell school-scraper-env # To setup the shell for this session
```

3. Install dependencies:
```bash
pip install -e .  # Installs in editable mode with dependencies from setup.py
```

### Running the Scraper

Basic usage:
```python
from src.scrapers.texas import TexasSchoolScraper, TexasSchoolEnricher

# Scrape basic data
scraper = TexasSchoolScraper()
scraper.run(
    filters=["Prekindergarten", "Kindergarten", "Early Education"],
    output_file="texas_schools_basic_data.csv"
)

# Enrich the data with additional information
enricher = TexasSchoolEnricher("texas_schools_basic_data.csv")
enricher.run()
```

## Library Choices and Trade-offs

### Selenium
**Pros:**
- Handles JavaScript-rendered content
- Supports complex interactions (clicking, form filling)
- Can automate browser actions
- Good for dynamic content

**Cons:**
- Slower than alternatives
- Resource-intensive
- Can be fragile with timing issues


### BeautifulSoup
**Pros:**
- Simple and intuitive API
- Great for parsing HTML
- Lightweight and fast
- Good documentation
- Works well with Selenium for parsing

**Cons:**
- Can't handle JavaScript-rendered content
- Limited to HTML parsing
- No built-in browser automation

## Future Improvements

### Orchestration
1. **Apache Airflow Integration**
Orchestration could be easily achivable by using cron but with Airflow we would get the following

   - DAG for each state's scraping pipeline
   - Automated scheduling and dataset aware execution
   - Retry mechanisms
   - Monitoring and alerting
   - Historical tracking

2. **Distributed Scraping**

With the current implementation the **enrichment process** is not parallelized. The enrichment process is currently sequential, meaning that it processes each school one at a time and gets pretty slow pretty fast. 

   - Multiple workers for parallel scraping

> [!TIP]
Although, currently, the scraping process parallelization could be achieved by spawning multiple scrapers if previously the csv file gets partitioned.

### Data Quality
1. **Validation Pipeline**
   - Schema validation
   - Data consistency checks
   - Duplicate detection
   - Address standardization
   - Phone number formatting

2. **Testing**
   - Unit tests for each component
   - Integration tests
   - Mock responses for testing
 

### Data Storage & Transformations
1. **Database Integration**
   - PostgreSQL or Apache Iceberg for structured data