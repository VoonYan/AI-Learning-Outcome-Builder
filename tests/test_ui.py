import subprocess
import time
import requests
import pytest
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import signal

base_url = "http://127.0.0.1:5000"

@pytest.fixture
def flask_server():
    """Start the Flask server in a subprocess."""
    env = os.environ.copy()
    env["FLASK_CONFIG"] = "testing"
    cmd = 'flask --app "app:create_app" run'

    if os.name == 'posix':
        proc = subprocess.Popen(
            cmd,
            shell=True,
            env=env,
            preexec_fn=os.setsid
        )
    if os.name == 'nt':
        proc = subprocess.Popen(
            cmd,
            shell=True,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    
    options = Options()
    options.add_argument("allow-running-insecure-content")

    timeout = 10
    while timeout > 0:
        try:
            requests.get(base_url)
            break
        except requests.ConnectionError:
            time.sleep(0.5)
            timeout -= 0.5
    else:
        proc.kill()
        raise RuntimeError("Flask server did not start in time.")
    
    yield

    # Cleanup
    if os.name == 'posix':
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    elif os.name == 'nt':        
        proc.send_signal(signal.CTRL_BREAK_EVENT)
        proc.terminate()
    
    proc.wait()


@pytest.fixture
def driver():
    """Start a Selenium WebDriver (Chrome)."""
    options = Options()
    options.add_argument("--headless")  # Run headless if needed
    options.add_argument("--window-size=1920,1080")  # Set viewport size

    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def login(driver):
    driver.get("http://127.0.0.1:5000/login_page")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    time.sleep(1)
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys('admin')
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys('password')

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

def test_signup(flask_server, driver):
    driver.get("http://127.0.0.1:5000/signup_page")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    time.sleep(1)

    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys('test')
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys('test')
    driver.find_element(By.ID, "confirmpassword").clear()
    driver.find_element(By.ID, "confirmpassword").send_keys('test')

    # Wait for button and click using JS to avoid overlay
    submit_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "submit"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
    driver.execute_script("arguments[0].click();", submit_btn)

    assert 'Account Created' in driver.page_source

def test_login(flask_server, driver):
    login(driver)
    assert 'Main Dashboard' in driver.page_source

def test_create_unit(flask_server, driver):
    # login before accessing protected page
    login(driver)
    driver.get(f"{base_url}/new_unit")

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "unitcode")))
    unit_code = "SELE1001"

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
    assert 'Unit Created' in driver.page_source

def search_unit(driver):
    driver.get("http://127.0.0.1:5000/search_unit")
    WebDriverWait(driver, 10).until(lambda d: "Unit Search" in d.title)
    query = driver.find_element(By.NAME, "query")
    query.send_keys('Professional')
    query.send_keys(Keys.ENTER)
    time.sleep(1)
    driver.find_element(By.LINK_TEXT, "Professional Computing [CITS3200]").click()
    WebDriverWait(driver, 10).until_not(EC.url_contains("/search_unit"))

def test_search_unit(flask_server, driver):
    search_unit(driver)
    assert 'Unit Details' in driver.page_source
    assert 'Professional Computing' in driver.page_source

def test_delete_unit(flask_server, driver):
    login(driver)
    search_unit(driver)
    driver.find_element(By.ID, "deleteUnitButton").click()
    alert = driver.switch_to.alert
    alert.accept()
    WebDriverWait(driver, 10).until_not(EC.url_contains("/view/"))
    assert 'Unit Deleted' in driver.page_source

def test_edit_unit(flask_server, driver):
    login(driver)
    search_unit(driver)
    driver.find_element(By.ID, "EditUnitButton").click()
    WebDriverWait(driver, 10).until_not(EC.url_contains("/view/"))

    driver.find_element(By.ID, "unitcode").send_keys('CITS320012')
    driver.find_element(By.ID, "unitname").send_keys("Test Unit Edit Selenium")
    Select(driver.find_element(By.ID, "levelSelect")).select_by_value("2")
    Select(driver.find_element(By.ID, "pointSelect")).select_by_value("12")
    submit_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "form button[type='submit'], form input[type='submit']"))
    )
    time.sleep(1)  # brief pause for stability
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
    driver.find_element(By.ID, "description").send_keys("Automated test editig")
    submit_button.click()

    WebDriverWait(driver, 10).until(EC.url_contains("/view/"))
    assert 'Unit updated successfully!' in driver.page_source

def test_add_and_edit_learning_outcome(flask_server, driver):
    login(driver)
    search_unit(driver)
    driver.find_element(By.ID, "EditLearningOutcomesButton").click()
    WebDriverWait(driver, 10).until_not(EC.url_contains("/view/"))
    

    # Wait for Add Outcome button and click
    add_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "addBtn"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", add_btn)
    add_btn.click()

    assert 'Outcome Added and Saved' in driver.page_source

    

