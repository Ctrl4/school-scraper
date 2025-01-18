"""
Texas-specific implementation of school scraping and enrichment.
"""

import re
import time
from typing import Dict, List

import pandas as pd
from base.base_scraper import BaseSchoolEnricher, BaseSchoolScraper
from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


class TexasSchoolScraper(BaseSchoolScraper):
    """Implementation of school scraper for Texas schools."""

    def __init__(self, headless: bool = True):
        super().__init__(headless)
        self.base_url = "https://txschools.gov/?view=schools&lng=en"

    def apply_filters(self, filters: List[str]):
        """Apply Texas-specific filters to the school search."""
        self.driver.get(self.base_url)

        filter_element = self.wait_for_element(
            By.XPATH, '//*[@placeholder="Select a grade level"]', condition="clickable"
        )

        for filter_value in filters:
            filter_element.click()
            filter_element.send_keys(filter_value)
            filter_element.send_keys(Keys.DOWN)
            filter_element.send_keys(Keys.RETURN)
            time.sleep(1)

    def _process_current_page(self):
        """Process all rows on the current page."""
        rows = self.driver.find_elements(By.XPATH, "//table//tbody/tr")

        for row in rows:
            try:
                url = row.find_element(By.XPATH, ".//td[1]//a").get_attribute("href")

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
                return self._process_current_page()
            except Exception as e:
                self.logger.error(f"Error processing row: {str(e)}")

    def _click_with_retry(self, element, max_retries=3):
        """Click an element with retry mechanism."""
        for attempt in range(max_retries):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView(true);", element
                )
                element.click()
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

    def get_table_data(self):
        """Extract school data from all pages."""
        while True:
            try:
                self.wait_for_element(
                    By.XPATH, "//table//tbody/tr", condition="presence"
                )
                self._process_current_page()

                next_button = self.wait_for_element(
                    By.XPATH,
                    "//button[contains(@aria-label, 'Go to next page')]",
                    condition="clickable",
                )

                if not next_button or "disabled" in next_button.get_attribute("class"):
                    self.logger.info("Reached last page")
                    break

                self._click_with_retry(next_button)
                self.current_page += 1
                self.logger.info(f"Moving to page {self.current_page}")

            except Exception as e:
                self.logger.error(f"Error during pagination: {str(e)}")
                break

    def run(self, filters: List[str], output_file: str):
        """Execute the Texas school scraping process."""
        try:
            self.setup_driver()
            self.apply_filters(filters)
            self.get_table_data()
            self.save_data(output_file)
            self.logger.info("Scraping completed successfully")
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
        finally:
            self.cleanup()


class TexasSchoolEnricher(BaseSchoolEnricher):
    """Implementation of school enricher for Texas schools."""

    def has_complete_data(self, row: pd.Series) -> bool:
        """Check if a school record already has complete data."""
        return pd.notna(row["phone"]) and pd.notna(row["website"])

    def extract_additional_data(self, row: pd.Series) -> Dict:
        """Extract additional data for a Texas school."""
        try:
            self.wait_for_element(By.CLASS_NAME, "jss16")

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Extract phone
            phone = None
            phone_section = soup.find(string=re.compile("PHONE:", re.IGNORECASE))
            if phone_section:
                phone_text = phone_section.find_next(string=True)
                if phone_text:
                    phone = phone_text.strip()

            # Extract website
            website = None
            website_button = soup.find(href=True, class_="MuiButtonBase-root")
            if website_button and website_button.get("href"):
                website = website_button["href"]

            return {"phone": phone, "website": website}

        except Exception as e:
            self.logger.error(f"Error extracting data: {str(e)}")
            return {"phone": None, "website": None}

    def log_final_statistics(
        self, df: pd.DataFrame, total_schools: int, output_file: str
    ):
        """Log final statistics about the enrichment process."""
        final_phones = len(df[df["phone"].notna()])
        final_websites = len(df[df["website"].notna()])

        self.logger.info(f"""
        Enrichment completed:
        - Total schools processed: {total_schools}
        - Schools with phone numbers: {final_phones}
        - Schools with websites: {final_websites}
        - Output saved to: {output_file}
        """)


if __name__ == "__main__":
    # Example usage
    scraper = TexasSchoolScraper()
    scraper.run(
        filters=["Prekindergarten", "Kindergarten", "Early Education"],
        output_file="texas_schools_basic_data.csv",
    )

    enricher = TexasSchoolEnricher("texas_schools_basic_data.csv")
    enricher.run()
