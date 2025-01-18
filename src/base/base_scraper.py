"""
Base classes for school scraping and enrichment functionality.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BaseWebDriver:
    """Base class for managing WebDriver setup and common operations."""

    def __init__(self, headless: bool = True):
        self.options = self._configure_chrome_options(headless)
        self.driver = None
        self.wait = None

        # Configure logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _configure_chrome_options(self, headless: bool) -> Options:
        """Configure Chrome WebDriver options."""
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1024,768")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return options

    def setup_driver(self):
        """Initialize WebDriver with configured options."""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def wait_for_element(
        self, by: By, selector: str, timeout: int = 10, condition: str = "presence"
    ) -> Optional[webdriver.remote.webelement.WebElement]:
        """Wait for an element with configurable conditions."""
        try:
            if condition == "clickable":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((by, selector))
                )
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
            return element
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {selector}")
            return None

    def cleanup(self):
        """Clean up WebDriver resources."""
        if self.driver:
            self.driver.quit()
            self.logger.info("WebDriver closed")


class BaseSchoolScraper(BaseWebDriver, ABC):
    """Abstract base class for school scraping functionality."""

    def __init__(self, headless: bool = True):
        super().__init__(headless)
        self.schools_data: List[Dict] = []
        self.processed_urls: Set[str] = set()
        self.current_page = 1

    @abstractmethod
    def apply_filters(self, filters: List[str]):
        """Apply filters to the school search."""
        pass

    @abstractmethod
    def get_table_data(self):
        """Extract school data from the current page."""
        pass

    def save_data(self, filename: str):
        """Save scraped data to CSV file."""
        df = pd.DataFrame(self.schools_data)
        df.to_csv(filename, index=False)
        self.logger.info(f"Data saved to {filename}")

    @abstractmethod
    def run(self, filters: List[str], output_file: str):
        """Execute the scraping process."""
        pass


class BaseSchoolEnricher(BaseWebDriver, ABC):
    """Abstract base class for enriching school data with additional information."""

    def __init__(self, input_csv: str, headless: bool = True):
        super().__init__(headless)
        self.input_csv = input_csv
        self.df = None
        self.processed_count = 0

    @abstractmethod
    def extract_additional_data(self, row: pd.Series) -> Dict:
        """Extract additional data for a school."""
        pass

    def process_school(self, row: pd.Series) -> pd.Series:
        """Process a single school and update its information."""
        try:
            self.logger.info(f"Processing school: {row['name']}")

            # Skip if already has complete data
            if self.has_complete_data(row):
                self.logger.info(f"Skipping {row['name']} - already has complete data")
                return row

            self.driver.get(row["url"])

            # Get additional data
            new_data = self.extract_additional_data(row)

            # Update row with new data
            for key, value in new_data.items():
                if value and pd.isna(row[key]):
                    row[key] = value
                    self.logger.info(f"Updated {key} for {row['name']}: {value}")

            time.sleep(1)  # Rate limiting
            self.processed_count += 1

            if self.processed_count % 10 == 0:
                self.logger.info(f"Processed {self.processed_count} schools")

            return row

        except Exception as e:
            self.logger.error(f"Error processing {row['name']}: {str(e)}")
            return row

    @abstractmethod
    def has_complete_data(self, row: pd.Series) -> bool:
        """Check if a school record already has complete data."""
        pass

    def run(self):
        """Main execution method."""
        try:
            # Load CSV
            self.logger.info(f"Loading data from {self.input_csv}")
            self.df = pd.read_csv(self.input_csv)
            total_schools = len(self.df)

            # Setup WebDriver
            self.setup_driver()

            # Process each school
            self.logger.info(f"Starting to process {total_schools} schools")
            updated_df = self.df.copy()

            for index, row in updated_df.iterrows():
                updated_row = self.process_school(row)
                updated_df.iloc[index] = updated_row

                # Save progress every 50 schools
                if (index + 1) % 50 == 0:
                    self.logger.info("Saving intermediate progress...")
                    updated_df.to_csv(f"intermediate_{self.input_csv}", index=False)

            # Save final results
            output_file = f"enriched_{self.input_csv}"
            updated_df.to_csv(output_file, index=False)

            self.log_final_statistics(updated_df, total_schools, output_file)

        except Exception as e:
            self.logger.error(f"Fatal error during enrichment: {str(e)}")
            raise

        finally:
            self.cleanup()

    @abstractmethod
    def log_final_statistics(
        self, df: pd.DataFrame, total_schools: int, output_file: str
    ):
        """Log final statistics about the enrichment process."""
        pass
