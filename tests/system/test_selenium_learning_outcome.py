import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import os
import time


# flow: login-> create new unit-> learning outcome
# for isolation, will make each test fullly independent

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

def create_unit(driver, base_url):
    # Step 1: Create a unit
    driver.get(f"{base_url}/new_unit")
    # Generate unique unit info
    unique_id = str(int(time.time()))
    unit_code = f"CS{unique_id[-6:]}"
    unit_name = f"Test Unit {unique_id}"

    # Wait until form is ready
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "unitcode"))
    )

    # Fill in the form fields 
    driver.find_element(By.ID, "unitcode").send_keys(unit_code)
    driver.find_element(By.ID, "unitname").send_keys(unit_name)
    driver.find_element(By.ID, "level").send_keys("3")
    driver.find_element(By.ID, "creditpoints").send_keys("6")
    driver.find_element(By.ID, "description").send_keys("Automatically created test unit")

    
    # --- wait and submit form ---
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "form"))
    )
    submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']"))
        )

    
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
    driver.execute_script("arguments[0].click();", submit_button)

    print("Submitted Add Unit form successfully")


# just stuck here. SOS

    # Wait for redirect to finish (the new unit form usually redirects)
    WebDriverWait(driver, 10).until(EC.url_changes(f"{base_url}/new_unit"))

    # Explicitly go to search page to locate the new unit
    driver.get(f"{base_url}/search_unit")

    # Step 3: Wait for search input and search for the created unit
    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "searchInput"))
    )
    search_input.clear()
    search_input.send_keys(unit_code)
    search_input.send_keys(Keys.RETURN)

    # Step 4: Wait for table to load and click on the created unit link
    link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/unit_details/') and contains(text(), '{unit_code}')]"))
    )
    link.click()

    # Step 5: On the unit details page, click “Edit Learning Outcomes”
    edit_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Edit Learning Outcomes')] | //button[contains(text(), 'Edit Learning Outcomes')]"))
    )
    edit_btn.click()

    # Step 6: Wait for the Learning Outcome page to load
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "addBtn")))
    print(f"Created and opened Learning Outcome Editor for {unit_code}")
    return unit_code


class TestLearningOutcome(unittest.TestCase):
    """System test for adding and saving learning outcomes."""

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

    def test_add_learning_outcome(self):
        driver = self.driver
        base_url = "http://127.0.0.1:5000"

        login(driver, base_url)
        print("Logged in at:", driver.current_url)

        unit_id = create_unit(driver, base_url)
        print("Unit created and opened LO editor:", driver.current_url)

        # Wait for Add Outcome button and click
        add_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "addBtn"))
        )
        add_btn.click()

        print("Added learning outcome successfully.")


if __name__ == "__main__":
    unittest.main(verbosity=2)