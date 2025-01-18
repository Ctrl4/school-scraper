import logging
import time

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class SchoolScraper:
    def __init__(self):
        # Initialize Chrome options
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--window-size=1024,768")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        self.schools_data = []
        
        # Add logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Pagination state
        self.current_page = 1
        self.processed_urls = set()

        # Add logging configuration
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Pagination state
        self.current_page = 1
        self.processed_urls = set()


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

    def apply_filters(self, filters):
        self.driver.get("https://txschools.gov/?view=schools&lng=en")

        # Wait for filter element
        filter_element = self.wait_for_element(
            By.XPATH, '//*[@placeholder="Select a grade level"]', condition="clickable"
        )

        for filter in filters:
            filter_element.click()
            filter_element.send_keys(filter)
            filter_element.send_keys(Keys.DOWN)
            filter_element.send_keys(Keys.RETURN)
            time.sleep(1)  # Small delay to let the filter apply

    def get_table_data(self):
        while True:
            try:
                # Wait for table to load
                self.wait_for_element(
                    By.XPATH, "//table//tbody/tr", condition="presence"
                )

                # Process current page
                self._process_current_page()

                # Check for next page button
                next_button = self.wait_for_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Go to next page')]",
                    condition="clickable",
                )

                if not next_button or "disabled" in next_button.get_attribute("class"):
                    self.logger.info("Reached last page")
                    break

                # Click next page with retry mechanism
                self._click_with_retry(next_button)

                self.current_page += 1
                self.logger.info(f"Moving to page {self.current_page}")

            except Exception as e:
                self.logger.error(f"Error during pagination: {str(e)}")
                break

    def _process_current_page(self):
        """Process all rows on current page"""
        rows = self.driver.find_elements(By.XPATH, "//table//tbody/tr")

        for row in rows:
            try:
                # Get URL first to check for duplicates
                url = row.find_element(By.XPATH, ".//td[1]//a").get_attribute("href")

                # Skip if already processed
                if url in self.processed_urls:
                    continue

                school_data = {
                    "name": row.find_element(By.XPATH, ".//td[1]//a").text,
                    "url": url,
                    "district": row.find_element(By.XPATH, ".//td[2]/a").text,
                    "address": row.find_element(By.XPATH, ".//td[3]/div").text,
                    "grades": row.find_element(By.XPATH, ".//td[4]").text,
                    "phone": None,
                    "website": None,
                    "page_number": self.current_page,
                }

                self.schools_data.append(school_data)
                self.processed_urls.add(url)
                self.logger.info(f"Processed school: {school_data['name']}")

            except StaleElementReferenceException:
                self.logger.warning("Encountered stale element, retrying page")
                self._process_current_page()
                break
            except Exception as e:
                self.logger.error(f"Error processing row: {str(e)}")

    def _click_with_retry(self, element, max_retries=3):
        """Click an element with retry mechanism"""
        for attempt in range(max_retries):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", element
                )
                element.click()
                # Wait for page to load after click
                self.wait_for_element(
                    By.XPATH, "//table//tbody/tr", condition="presence"
                )
                return True
            except (
                ElementClickInterceptedException,
                StaleElementReferenceException,
            ) as e:
                if attempt == max_retries - 1:
                    raise e
                self.logger.warning(
                    f"Click failed, attempt {attempt + 1} of {max_retries}"
                )
                time.sleep(1)

    def save_data(self, filename):
        # Convert the list of dictionaries to a pandas DataFrame
        df = pd.DataFrame(self.schools_data)

        # Save as CSV
        df.to_csv(filename, index=False)
        self.logger.info(f"Data saved to {filename}")

    def run(self):
        try:
            filters = ["Prekindergarten", "Kindergarten", "Early Education"]
            self.apply_filters(filters)
            self.get_table_data()
            self.save_data("schools_basic_data.csv")
            self.logger.info("Scraping completed successfully")
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
        finally:
            self.driver.quit()


if __name__ == "__main__":
    scraper = SchoolScraper()
    scraper.run()
