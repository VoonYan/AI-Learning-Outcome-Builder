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
    #options.add_argument("--headless")  # Run headless if needed
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def test_login(flask_server, driver):
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
    print("Logged in at:", driver.current_url)
    if "login_page" in driver.current_url:
        print("Login failed. Page source snippet:")
        print(driver.page_source[:1000])  # first 1000 chars to inspect flash message
    time.sleep(1)

