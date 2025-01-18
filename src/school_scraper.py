from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import pandas as pd
import time

class SchoolScraper:
    def __init__(self):
        # Configure Chrome options
        self.options = Options()
        self.options.add_argument("--window-size=1024,768")
        
        self.driver = webdriver.Chrome(options=self.options)
        self.wait = WebDriverWait(self.driver, 10)
        self.schools_data = []


    def apply_filters(self, filters):
        self.driver.get("https://txschools.gov/?view=schools&lng=en")
        
        # Wait for filter element
        filter_element = self.wait.until(
            EC.visibility_of_element_located((By.XPATH, '//*[@placeholder="Select a grade level"]'))
        )

        for filter in filters:
            filter_element.click()
            filter_element.send_keys(filter)
            filter_element.send_keys(Keys.DOWN)
            filter_element.send_keys(Keys.RETURN)
            time.sleep(1)  # Small delay to let the filter apply

    def get_table_data(self):
        # Wait for table to load
        self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//table//tbody/tr"))
        )
        
        # Get all rows
        rows = self.driver.find_elements(By.XPATH, "//table//tbody/tr")
        
        for row in rows:
            try:
                school_data = {
                    'name': row.find_element(By.XPATH, ".//td[1]//a").text,
                    'url': row.find_element(By.XPATH, ".//td[1]//a").get_attribute('href'),
                    'district': row.find_element(By.XPATH, ".//td[2]/a").text,
                    'address': row.find_element(By.XPATH, ".//td[3]/div").text,
                    'grades': row.find_element(By.XPATH, ".//td[4]").text,
                    'phone': None,
                    'website': None
                }
                self.schools_data.append(school_data)
            except Exception as e:
                print(f"Error processing row: {e}")

    def save_data(self, filename):
        # Convert the list of dictionaries to a pandas DataFrame
        df = pd.DataFrame(self.schools_data)
        
        # Save as CSV
        df.to_csv(filename, index=False)

    def run(self):
        try:
            filters = ["Prekindergarten", "Kindergarten", "Early Education"]
            self.apply_filters(filters)
            self.get_table_data()
            self.save_data('schools_basic_data.csv')
        finally:
            self.driver.quit()

if __name__ == "__main__":
    scraper = SchoolScraper()
    scraper.run()