import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import os
import time


class TestLearningOutcome(unittest.TestCase):
    """System test for adding and deleting learning outcomes."""

    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1400,900")
        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_add_learning_outcome(self):
        driver = self.driver
        driver.get(f"{self.base_url}/create_lo/1")  # example unit ID
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "addBtn"))
        ).click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#lo-tbody tr[data-id]"))
        )
        desc_div = driver.find_element(
            By.CSS_SELECTOR, "#lo-tbody tr[data-id]:first-child td.loDesc [contenteditable]"
        )
        desc_div.click()
        desc_div.send_keys(Keys.CONTROL + "a")
        desc_div.send_keys("New Selenium LO")

        driver.find_element(By.ID, "saveBtn").click()
        time.sleep(1)
        self.assertIn("New Selenium LO", driver.page_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
