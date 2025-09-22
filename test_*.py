import uuid
import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WAIT = 15

def wait_click(driver, by, sel):
    el = WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((by, sel)))
    el.click()
    return el

def wait_type(driver, by, sel, text, clear=True):
    el = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((by, sel)))
    if clear:
        el.clear()
    el.send_keys(text)
    return el

def wait_for_text(driver, text):
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, f"//*[contains(normalize-space(.), '{text}')]"))
    )

def login(driver, base_url, username, password):
    driver.get(f"{base_url}/login")
    wait_type(driver, By.NAME, "username", username)
    wait_type(driver, By.NAME, "password", password)
    wait_click(driver, By.XPATH, "//button[@type='submit' or contains(., 'Login')]")
    wait_for_text(driver, "Main Dashboard")

def goto_new_unit(driver, base_url):
    driver.get(f"{base_url}/new_unit")

def create_unit(driver, base_url):
    goto_new_unit(driver, base_url)
    code = f"AUTO{uuid.uuid4().hex[:6].upper()}"
    wait_type(driver, By.NAME, "unitcode", code)
    wait_type(driver, By.NAME, "unitname", "Automated Test Unit")
    wait_type(driver, By.NAME, "level", "1")
    wait_type(driver, By.NAME, "creditpoints", "6")
    wait_type(driver, By.NAME, "description", "Created by Selenium E2E test.")
    wait_click(driver, By.XPATH, "//button[@type='submit' or contains(., 'Create') or contains(., 'Save')]")
    try:
        wait_for_text(driver, "success")
    except:
        wait_for_text(driver, "Main Dashboard")
    return code

def search_unit(driver, base_url, code):
    driver.get(f"{base_url}/search_unit?query={code}&filter=code")
    wait_for_text(driver, code)

def open_lo_editor_for_unit(driver, base_url, code):
    try:
        wait_click(driver, By.XPATH, f"//a[contains(., '{code}')]/ancestor::*[self::tr or self::div][1]//a[contains(., 'Learning Outcome Editor') or contains(., 'Edit')]")
    except:
        driver.get(f"{base_url}/create_lo?unitcode={code}")
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "addBtn")))

def create_lo(driver, description="Outcome from E2E", assessment="Exam", position="1"):
    wait_click(driver, By.ID, "addBtn")
    wait_type(driver, By.NAME, "description", description)
    try:
        wait_type(driver, By.NAME, "assessment", assessment)
    except:
        pass
    try:
        wait_type(driver, By.NAME, "position", position)
    except:
        pass
    wait_click(driver, By.XPATH, "//button[contains(., 'Save') or contains(., 'Update')]")
    wait_for_text(driver, description)

def edit_lo(driver, old_text, new_text):
    wait_click(driver, By.XPATH, f"//*[contains(normalize-space(.), '{old_text}')]/ancestor::*[self::tr or self::div][1]//button[contains(., 'Edit') or contains(., 'Update')]")
    wait_type(driver, By.NAME, "description", new_text)
    wait_click(driver, By.XPATH, "//button[contains(., 'Save') or contains(., 'Update')]")
    wait_for_text(driver, new_text)

def delete_lo(driver, text):
    wait_click(driver, By.XPATH, f"//*[contains(normalize-space(.), '{text}')]/ancestor::*[self::tr or self::div][1]//button[contains(., 'Delete') or contains(., 'Remove')]")
    try:
        wait_click(driver, By.XPATH, "//button[contains(., 'Confirm') or contains(., 'Yes')]")
    except:
        pass
    time.sleep(1)
    els = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(.), '{text}')]")
    assert not els, "Learning Outcome still visible after delete"

def delete_unit(driver, base_url, code):
    search_unit(driver, base_url, code)
    wait_click(driver, By.XPATH, f"//*[contains(., '{code}')]/ancestor::*[self::tr or self::div][1]//button[contains(., 'Delete') or contains(., 'Remove')]")
    try:
        wait_click(driver, By.XPATH, "//button[contains(., 'Confirm') or contains(., 'Yes')]")
    except:
        pass
    driver.get(f"{base_url}/search_unit?query={code}&filter=code")
    time.sleep(1)
    els = driver.find_elements(By.XPATH, f"//*[contains(., '{code}')]")
    assert not els, "Unit still visible after delete"

@pytest.mark.e2e
def test_full_flow(driver, base_url, creds):
    login(driver, base_url, creds["username"], creds["password"])
    code = create_unit(driver, base_url)
    search_unit(driver, base_url, code)
    open_lo_editor_for_unit(driver, base_url, code)
    lo_text = "Outcome from E2E"
    create_lo(driver, description=lo_text)
    edited = "Outcome edited by E2E"
    edit_lo(driver, lo_text, edited)
    delete_lo(driver, edited)
    delete_unit(driver, base_url, code)