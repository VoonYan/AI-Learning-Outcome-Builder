import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import os
import time


class TestCreateUnit(unittest.TestCase):
    """System test for creating a new unit."""

    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_create_unit(self):
        driver = self.driver
        driver.get(f"{self.base_url}/new_unit")

        driver.find_element(By.ID, "unitcode").send_keys("TST001")
        driver.find_element(By.ID, "unitname").send_keys("Test Unit Selenium")
        Select(driver.find_element(By.ID, "level")).select_by_value("1")
        Select(driver.find_element(By.ID, "creditpoints")).select_by_value("6")
        driver.find_element(By.ID, "description").send_keys("Automated test")

        driver.find_element(By.CSS_SELECTOR, "form button[type='submit']").click()

        WebDriverWait(driver, 10).until(
            lambda d: "/new_unit" not in d.current_url
        )
        self.assertNotIn("/new_unit", driver.current_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
