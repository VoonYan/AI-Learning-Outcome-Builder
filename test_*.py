import uuid
import time
import pytest
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import random, string, sys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import re

'''

What it does:
Logs in (POST /login_page → 302 → /dashboard).
Creates a unit (POST /new_unit → 302 → /main_page).
Finds the unit in search.
Opens the unit detail (/view/6629) and LO editor (/create_lo/6629).
Clicks Add Outcome (POST /lo_api/add/6629 → 200), and the LO editor reloads.

What it can’t do yet:
After Add Outcome, the test can’t find the new LO row using "#lo-tbody tr[data-id]". 
DOM selectors don’t match the actual page, so it times out before editing/saving.


'''
WAIT = 10

def dump_debug(driver, label):
    out = Path("tests/.artifacts")
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / f"{label}.html"
    png_path = out / f"{label}.png"
    html_path.write_text(driver.page_source, encoding="utf-8")
    try:
        driver.save_screenshot(str(png_path))
    except Exception:
        pass
    print(f"[debug] saved {html_path} and {png_path}")

def wait_click(driver, by, sel):
    el = WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((by, sel)))
    el.click()
    return el




def wait_type(driver, by, sel, text, clear=True):
    el = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((by, sel)))
    tag = (el.tag_name or "").lower()
    el_type = (el.get_attribute("type") or "").lower()
    name_attr = el.get_attribute("name") or sel

    # Handle <select>
    if tag == "select":
        s = Select(el)
        try:
            s.select_by_visible_text(str(text))
        except Exception:
            s.select_by_value(str(text))
        return el

    # Handle radios/checkboxes
    if el_type in ("radio", "checkbox"):
        try:
            opt = driver.find_element(By.XPATH, f"//input[@name='{name_attr}' and @value='{text}']")
            WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((By.XPATH, f"//input[@name='{name_attr}' and @value='{text}']"))).click()
            return opt
        except Exception:
            pass

    # Safe clear for inputs (number/text) and textareas
    if clear:
        try:
            el.clear()
        except Exception:
            # Fallback: select-all then type
            mod = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
            try:
                el.send_keys(mod + "a")
            except Exception:
                pass

    # Type the value (works for number/text)
    try:
        el.send_keys(str(text))
    except Exception as e:
        # Last resort: set via JS and fire input event
        try:
            driver.execute_script(
                "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true}));",
                el,
                str(text),
            )
        except Exception:
            dump_debug(driver, f"set_value_failed_{name_attr}")
            raise e
    return el

def wait_for_text(driver, text):
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, f"//*[contains(normalize-space(.), '{text}')]"))
    )
def wait_title_contains(driver, text):
    WebDriverWait(driver, WAIT).until(EC.title_contains(text))




def login(driver, base_url, username, password):
    driver.get(f"{base_url}/login_page")

    # Locate the form and fields by name/id
    form = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, "//form"))
    )
    user_el = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, "//input[@name='username' or @id='username' or @name='email' or @id='email']"))
    )
    pw_el = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='password' or @id='password']"))
    )

    try: user_el.clear()
    except: pass
    user_el.send_keys(username)
    try: pw_el.clear()
    except: pass
    pw_el.send_keys(password)

    # Submit: prefer exact submit input/button; else JS submit
    submitted = False
    for by, sel in [
        (By.ID, "submit"),
        (By.XPATH, "//form//button[@type='submit']"),
        (By.XPATH, "//form//input[@type='submit']"),
    ]:
        try:
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, sel))).click()
            submitted = True
            break
        except Exception:
            continue
    if not submitted:
        # fallback: submit the form via JS
        driver.execute_script("arguments[0].submit();", form)

    # Success criteria: Logout link, or title not containing Login, or user menu present
    try:
        WebDriverWait(driver, WAIT).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Logout') or contains(., 'Sign out')]"))
        )
        return
    except Exception:
        pass

    try:
        WebDriverWait(driver, WAIT).until(lambda d: 'login' not in d.current_url.lower() and 'Login' not in d.title)
        return
    except Exception:
        # Capture any error/flash messages to help debug credentials/validation
        errors = []
        for xp in [
            "//*[@class[contains(., 'alert')]]",
            "//*[@class[contains(., 'error')]]",
            "//*[@class[contains(., 'invalid-feedback')]]",
            "//*[contains(., 'invalid') or contains(., 'Incorrect') or contains(., 'error') or contains(., 'failed')]",
        ]:
            try:
                els = driver.find_elements(By.XPATH, xp)
                errors.extend([e.text.strip() for e in els if e.text.strip()])
            except Exception:
                pass

        dump_debug(driver, "login_failed")
        raise AssertionError(f"Login didn’t succeed. URL={driver.current_url}, title='{driver.title}', errors={errors}")



def goto_new_unit(driver, base_url):
    driver.get(f"{base_url}/new_unit")




def wait_click(driver, by, sel):
    el = WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((by, sel)))
    WebDriverWait(driver, WAIT).until(EC.visibility_of(el))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((by, sel)))
        el.click()
    except Exception:
        try:
            ActionChains(driver).move_to_element(el).pause(0.1).click(el).perform()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
    return el





def _force_click(driver, el):
    # Scroll into view
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    # Try a normal click
    try:
        el.click()
        return True
    except Exception:
        pass
    # Temporarily disable any overlay at the click point
    try:
        driver.execute_script("""
            const el = arguments[0];
            const r = el.getBoundingClientRect();
            const cx = r.left + r.width/2, cy = r.top + Math.min(r.height/2, 10);
            const top = document.elementFromPoint(cx, cy);
            if (top && top !== el) top.style.pointerEvents = 'none';
        """, el)
    except Exception:
        pass
    # Try ActionChains click
    try:
        ActionChains(driver).move_to_element(el).pause(0.05).click(el).perform()
        return True
    except Exception:
        pass
    # JS click as last resort
    try:
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        return False

def create_unit(driver, base_url):
    driver.get(f"{base_url}/new_unit")

    # Grab the exact form by action and cache current url and csrf to detect reload/redirect
    form = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "form[action='/new_unit']"))
    )
    old_url = driver.current_url
    try:
        old_csrf = form.find_element(By.NAME, "csrf_token").get_attribute("value")
    except Exception:
        old_csrf = ""

    # Generate unique code
    unit_code = "T" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Fill fields by exact IDs
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "unitcode"))).clear()
    driver.find_element(By.ID, "unitcode").send_keys(unit_code)

    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "unitname"))).clear()
    driver.find_element(By.ID, "unitname").send_keys("E2E Test Unit")

    Select(WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "level")))).select_by_value("1")
    Select(WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "creditpoints")))).select_by_value("6")

    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "description"))).clear()
    driver.find_element(By.ID, "description").send_keys("Automated test unit")

    # Submit the form robustly: requestSubmit/submit instead of clicking
    driver.execute_script("""
        const form = arguments[0];
        form.noValidate = true; form.setAttribute('novalidate','novalidate');
        try { if (form.requestSubmit) form.requestSubmit(); else form.submit(); }
        catch(e){ form.submit(); }
    """, form)

    # Wait for redirect or at least a full reload (csrf changes)
    try:
        WebDriverWait(driver, WAIT).until(
            lambda d: "/new_unit" not in d.current_url.lower()
                      or d.execute_script("const el=document.querySelector(\"input[name='csrf_token']\"); return el && el.value !== arguments[0];", old_csrf)
        )
    except Exception:
        dump_debug(driver, "create_unit_after_submit")
        msgs = [e.text for e in driver.find_elements(By.CSS_SELECTOR, ".alert, .invalid-feedback, .text-danger, .help-block")]
        raise AssertionError(f"Unit creation did not submit (no POST/redirect). Messages: {msgs}")

    return unit_code


def search_unit(driver, base_url, code):
    driver.get(f"{base_url}/search_unit?query={code}&filter=code")
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, f"//*[contains(normalize-space(.), '{code}')]"))
    )
    dump_debug(driver, f"search_results_{code}")




def open_lo_editor_for_unit(driver, base_url, code):
    # Go to search and click the unit details link (/view/<id>)
    driver.get(f"{base_url}/search_unit?query={code}&filter=code")
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, f"//*[contains(normalize-space(.), '{code}')]"))
    )
    # Prefer a /view/ link that contains the code; fallback to first /view/
    try:
        a = WebDriverWait(driver, WAIT).until(
            EC.element_to_be_clickable((By.XPATH, f"(//a[contains(@href, '/view/')][contains(., '{code}')])[1]"))
        )
    except Exception:
        a = WebDriverWait(driver, WAIT).until(
            EC.element_to_be_clickable((By.XPATH, "(//a[contains(@href, '/view/')])[1]"))
        )
    href = a.get_attribute("href") or ""
    m = re.search(r"/view/(\d+)", href)
    unit_id = m.group(1) if m else None
    try:
        a.click()
    except Exception:
        driver.execute_script("arguments[0].click();", a)

    # On the view page, click the LO editor link or go directly to /create_lo/<id>
    try:
        edit = WebDriverWait(driver, WAIT).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/create_lo/') or contains(., 'Edit Learning Outcomes')]"))
        )
        try:
            edit.click()
        except Exception:
            driver.execute_script("arguments[0].click();", edit)
    except Exception:
        if not unit_id:
            dump_debug(driver, "lo_editor_nav_failed")
            raise AssertionError("No LO editor link and unit id unknown")
        driver.get(f"{base_url}/create_lo/{unit_id}")

    # LO editor is loaded when #addBtn is present
    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.ID, "addBtn")))

def create_lo(driver, description, assessment="", position="1"):
    # Click Add Outcome (page reloads after fetch)
    WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((By.ID, "addBtn"))).click()
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#lo-tbody tr[data-id]"))
    )

    # Edit first row
    desc_div = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#lo-tbody tr[data-id]:first-child td.loDesc [contenteditable]"))
    )
    desc_div.click()
    desc_div.send_keys(Keys.COMMAND + "a")
    desc_div.send_keys(description)

    if assessment:
        ass_div = WebDriverWait(driver, WAIT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#lo-tbody tr[data-id]:first-child td.loAss [contenteditable]"))
        )
        ass_div.click()
        ass_div.send_keys(Keys.COMMAND + "a")
        ass_div.send_keys(assessment)

    # Save (sendSaveRequest + alert)
    try:
        WebDriverWait(driver, WAIT).until(EC.element_to_be_clickable((By.ID, "saveBtn"))).click()
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            driver.switch_to.alert.accept()
        except Exception:
            pass
    except Exception:
        pass

    # Verify description appears
    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, f"//td[contains(@class,'loDesc')]//*[contains(., '{description}')]"))
    )

def delete_lo(driver, text):
    row = WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.XPATH, f"//tr[td[contains(@class,'loDesc')]//*[contains(normalize-space(.), '{text}')]]"))
    )
    btn = row.find_element(By.CSS_SELECTOR, "button.btn.btn-danger")
    btn.click()
    WebDriverWait(driver, 5).until(EC.alert_is_present())
    driver.switch_to.alert.accept()
    WebDriverWait(driver, WAIT).until_not(
        EC.presence_of_element_located((By.XPATH, f"//tr[td[contains(@class,'loDesc')]//*[contains(normalize-space(.), '{text}')]]"))
    )
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