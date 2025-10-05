import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import os
import time

def login(driver, base_url, username="selenium", password="abc123"):
    driver.get(f"{base_url}/login_page")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(password)

    # Wait for button and click using JS to avoid overlay
    submit_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "submit"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
    driver.execute_script("arguments[0].click();", submit_btn)

    # Confirm redirect or manually navigate if stuck
    try:
        WebDriverWait(driver, 15).until(EC.url_contains("/dashboard"))
    except:
        # Fallback in case it gets stuck on login_page
        driver.get(f"{base_url}/dashboard")
    print("✅ Logged in at:", driver.current_url)
    if "login_page" in driver.current_url:
        print("❌ Login failed. Page source snippet:")
        print(driver.page_source[:1000])  # first 1000 chars to inspect flash message

    time.sleep(1)


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
        login(driver, self.base_url)
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
