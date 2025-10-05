import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
# created admin account, username: selenium, password: abc123

class TestLogin(unittest.TestCase):
    """System test for login functionality."""

    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1400,900")
        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000")
        cls.username = os.getenv("TEST_USERNAME", "selenium")
        cls.password = os.getenv("TEST_PASSWORD", "abc123")
# seems wrong password or account not match
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_login_success(self):
        driver = self.driver
        driver.get(f"{self.base_url}/login_page")

        driver.find_element(By.NAME, "username").send_keys(self.username)
        driver.find_element(By.NAME, "password").send_keys(self.password)
        driver.find_element(By.ID, "submit").click()

        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        self.assertIn("/dashboard", driver.current_url, "Login failed")

    def test_login_fail(self):
        driver = self.driver
        driver.get(f"{self.base_url}/login_page")

        driver.find_element(By.NAME, "username").send_keys("fakeuser")
        driver.find_element(By.NAME, "password").send_keys("wrongpass")
        driver.find_element(By.ID, "submit").click()

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".alert, .text-danger"))
        )
        self.assertIn("Login Failed", driver.page_source)



if __name__ == "__main__":
    unittest.main(verbosity=2)
