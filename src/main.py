"""
Example usage of the school scraper framework.
"""
from scrapers.texas import TexasSchoolScraper, TexasSchoolEnricher

def scrape_texas_schools():
    # Scrape basic data
    scraper = TexasSchoolScraper(headless=False)
    scraper.run(
        filters=["Prekindergarten", "Kindergarten", "Early Education"],
        output_file="texas_schools_basic_data.csv"
    )

    # Enrich data
    enricher = TexasSchoolEnricher("texas_schools_basic_data.csv")
    enricher.run()


if __name__ == "__main__":
    # Run scraper for desired state
    scrape_texas_schools()
  