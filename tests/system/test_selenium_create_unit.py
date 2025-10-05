import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import os
import time
# manually checked: can see the new unit now
# flow: login -> create unit
# each test will create a new unit with unique code

class TestCreateUnit(unittest.TestCase):

    @staticmethod
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


        try:
            WebDriverWait(driver, 15).until(EC.url_contains("/dashboard"))
        except:
            # Fallback in case it gets stuck on login_page
            driver.get(f"{base_url}/dashboard") 
        print("Logged in at:", driver.current_url)
        if "login_page" in driver.current_url:
            print("Login failed. Page source snippet:")
            print(driver.page_source[:1000])  # first 1000 chars to inspect flash message
        time.sleep(1)



    @classmethod
    def setUpClass(cls):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")

        options.add_argument("--window-size=1920,1080")
        cls.driver = webdriver.Chrome(options=options)
        cls.base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000")

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_create_unit(self):
        driver = self.driver
        # login before accessing protected page
        self.login(driver, self.base_url)
        driver.get(f"{self.base_url}/new_unit")

        

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "unitcode")))
        # driver.find_element(By.ID, "unitcode").send_keys("TST001")
        unit_code = f"TST{int(time.time()) % 10000}"  # unique every run

        driver.find_element(By.ID, "unitcode").send_keys(unit_code)
        driver.find_element(By.ID, "unitname").send_keys("Test Unit Selenium")
        Select(driver.find_element(By.ID, "level")).select_by_value("1")
        Select(driver.find_element(By.ID, "creditpoints")).select_by_value("6")
        driver.find_element(By.ID, "description").send_keys("Automated test")
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(0.5)  # brief pause for stability
        submit_button.click()


        WebDriverWait(driver, 10).until_not(EC.url_contains("/new_unit"))
        self.assertNotIn("/new_unit", driver.current_url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
