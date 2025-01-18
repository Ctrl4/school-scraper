import logging
import re
import time

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class SchoolEnricher:
    def __init__(self, input_csv):
        self.input_csv = input_csv

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            # filename='school_enrichment.log'
        )
        self.logger = logging.getLogger(__name__)

        # Initialize Chrome options
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--window-size=1024,768")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")

        self.driver = None
        self.wait = None
        self.df = None
        self.processed_count = 0

    def setup_driver(self):
        """Initialize webdriver with configured options"""
        try:
            self.driver = webdriver.Chrome(options=self.options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def wait_for_element(self, by, selector, timeout=10, condition="presence"):
        """Wait for an element with configurable conditions"""
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

    def extract_phone_website(self):
        """Extract phone and website information from the loaded page"""
        try:
            # Wait for content to load
            self.wait_for_element(By.CLASS_NAME, "jss16")

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            # Find phone number - looking for text after "PHONE:" label
            phone = None
            phone_section = soup.find(string=re.compile("PHONE:", re.IGNORECASE))
            if phone_section:
                # Get the next sibling text which contains the phone number
                phone_text = phone_section.find_next(string=True)
                if phone_text:
                    phone = phone_text.strip()

            # Extract website
            website = None
            website_button = soup.find(href=True, class_="MuiButtonBase-root")
            if website_button and website_button.get("href"):
                website = website_button["href"]

            return phone, website

        except Exception as e:
            self.logger.error(f"Error extracting data: {str(e)}")
            return None, None

    def process_school(self, row):
        """Process a single school and update its information"""
        try:
            self.logger.info(f"Processing school: {row['name']}")

            # Skip if already has both phone and website
            if pd.notna(row["phone"]) and pd.notna(row["website"]):
                self.logger.info(f"Skipping {row['name']} - already has complete data")
                return row

            self.driver.get(row["url"])

            phone, website = self.extract_phone_website()

            # Update only if new data is found and current is empty
            if phone and pd.isna(row["phone"]):
                row["phone"] = phone
                self.logger.info(f"Updated phone for {row['name']}: {phone}")

            if website and pd.isna(row["website"]):
                row["website"] = website
                self.logger.info(f"Updated website for {row['name']}: {website}")

            time.sleep(1)  # Rate limiting
            self.processed_count += 1

            if self.processed_count % 10 == 0:
                self.logger.info(f"Processed {self.processed_count} schools")

            return row

        except Exception as e:
            self.logger.error(f"Error processing {row['name']}: {str(e)}")
            return row

    def run(self):
        """Main execution method"""
        try:
            # Load CSV
            self.logger.info(f"Loading data from {self.input_csv}")
            self.df = pd.read_csv(self.input_csv)
            total_schools = len(self.df)

            # Setup WebDriver
            self.setup_driver()

            # Process each school
            self.logger.info(f"Starting to process {total_schools} schools")

            # Create a copy to work with
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

            # Log final statistics
            final_phones = len(updated_df[updated_df["phone"].notna()])
            final_websites = len(updated_df[updated_df["website"].notna()])

            self.logger.info(f"""
            Enrichment completed:
            - Total schools processed: {total_schools}
            - Schools with phone numbers: {final_phones}
            - Schools with websites: {final_websites}
            - Output saved to: {output_file}
            """)

        except Exception as e:
            self.logger.error(f"Fatal error during enrichment: {str(e)}")
            raise

        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed")


if __name__ == "__main__":
    enricher = SchoolEnricher("schools_basic_data.csv")
    enricher.run()
