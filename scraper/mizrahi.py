import logging
from os import environ

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, \
    WebDriverException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from scraper.common import ScrapeResults, find_element_by_text, safe_click, \
    clean_float

log = logging.getLogger(__name__)


def scrape(target, capabilities):
    result = ScrapeResults()
    result.bank = 'Mizrahi Tefahot'
    driver = webdriver.Remote(
        command_executor=target,
        desired_capabilities=capabilities,
    )
    driver.maximize_window()
    driver.get("https://www.mizrahi-tefahot.co.il/")
    try:
        scrape_detect_login(driver)
        scrape_perform_login(driver)
        return scrape_process(driver, result)

    finally:
        driver.quit()


def scrape_detect_login(driver: WebDriver):
    log.debug("starting login")
    if '/loginca/' in driver.current_url:
        log.debug("detected legacy login page, redirecting to home page")
        driver.find_element(
            by=By.CLASS_NAME,
            value="home-page-link",
        ).click()
    login_button = driver.find_element(by=By.ID, value="logInBtn")
    log.debug("found login button")
    assert login_button.text == "כניסה לחשבון"
    log.debug("login text matches, proceeding")
    safe_click(driver, login_button)


def scrape_perform_login(driver: WebDriver):
    driver.implicitly_wait(2)

    log.debug("waiting for login popup dialog")
    WebDriverWait(driver, 60).until(
        ec.invisibility_of_element_located((By.CLASS_NAME, "sk-ball-spin"))
    )
    log.debug("login popup dialog detected")

    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, "iframe"))
    username_f = driver.find_element(by=By.CLASS_NAME, value="input_user")
    password_f = driver.find_element(by=By.CLASS_NAME, value="input_pass")
    username = environ.get("MIZRAHI_USERNAME")
    assert username
    password = environ.get("MIZRAHI_PASSWORD")
    assert password
    username_f.send_keys(username)
    password_f.send_keys(password)
    password_f.send_keys(Keys.RETURN)
    driver.switch_to.default_content()
    log.debug("username and password submitted")


def scrape_process(driver: WebDriver, result: ScrapeResults):
    driver.implicitly_wait(10)

    log.debug("waiting for main website to load")
    exit_button = WebDriverWait(driver, 60).until(
        ec.element_to_be_clickable((By.CLASS_NAME, "lnkExitWebSite"))
    )
    log.debug("main website loaded")

    result.account = driver.find_element(
        By.XPATH,
        '//div[@class="containerKendoSelect"]/span/span/span/div/span',
    ).text
    assert result.account

    try:
        for btn in driver.find_elements(
                By.ID, "ctl00_ContentPlaceHolder2_btnSave"
        ):
            log.debug("skipping details confirmation request dialog")
            safe_click(driver, btn)

        process_chequing_nis(driver, result)

        process_chequing_foreign(driver, result)

        process_stocks(driver, result)

        return result

    finally:
        if exit_button:
            try:
                driver.implicitly_wait(1)
                exit_button.click()
                driver.implicitly_wait(20)
                driver.find_element(by=By.CLASS_NAME, value="goToLogin")
            except WebDriverException:
                pass


def process_chequing_nis(driver: WebDriver, result: ScrapeResults):
    log.debug("switching to chequing account")
    safe_click(driver, find_element_by_text(
        driver,
        By.CSS_SELECTOR,
        "#mainMenu > ul > li > a",
        "עובר ושב"
    ))
    # safe_click(driver, driver.find_element(
    #     by=By.CSS_SELECTOR,
    #     value="#mainMenu > ul > li:nth-child(2) > a"
    # ))  # עובר ושב

    log.debug("detecting nis balance")
    nis_balance = find_element_by_text(driver, By.CLASS_NAME, "sky-big3", "₪",
                                       exact=False)
    result.nis = clean_float(nis_balance.text)
    log.debug("loading nis transactions from past year")
    safe_click(driver, find_element_by_text(
        driver,
        By.CSS_SELECTOR,
        "ul.sub-menu-items > li > a",
        "יתרה ותנועות בחשבון"
    ))
    safe_click(driver, find_element_by_text(
        driver,
        By.CSS_SELECTOR,
        ".linkPannel > button",
        "שנה אחורה"
    ))

    for checkbox in ("checkAsmachta", "checkTnuotHayomKodmot"):
        element = WebDriverWait(driver, 10).until(
            ec.element_to_be_clickable((By.ID, checkbox))
        )
        if not element.get_attribute('checked'):
            log.debug(f"clicking unchecked element {checkbox}")
            safe_click(driver, element)

    WebDriverWait(driver, 30).until(
        ec.presence_of_all_elements_located((By.CLASS_NAME, "k-master-row"))
    )
    # for _ in range(3):
    #     try:
    #         driver.find_elements(by=By.CLASS_NAME, value="k-master-row")[
    #             0].get_property('cells')[0].accessible_name
    #         break
    #     except (StaleElementReferenceException, WebDriverException):
    #         pass

    for row in driver.find_elements(By.CLASS_NAME, "k-master-row"):
        cells = row.get_property('cells')
        if len(cells) != 9:
            continue
        result.transactions['nis'].append(
            {
                cell.accessible_name: cell.text
                for cell in cells
                if cell.accessible_name
            }
        )
    # todo: handle next page button


def process_chequing_foreign(driver: WebDriver, result: ScrapeResults):
    safe_click(driver, find_element_by_text(
        driver, By.CLASS_NAME, "sub-menu-parent", "עו''ש מט''ח"
    ))
    safe_click(
        driver,
        find_element_by_text(
            driver,
            By.CSS_SELECTOR,
            "ul.sub-menu-items > li > a",
            "יתרות בחשבון"
        )
    )

    try:
        driver.implicitly_wait(0)
        driver.find_element(By.CLASS_NAME, "error_msg")
        return
    except NoSuchElementException:
        pass

    driver.implicitly_wait(10)
    driver.switch_to.frame("contentFrame")
    currencies = len(driver.find_elements(By.CLASS_NAME, "header3")) - 1

    for nth in range(0, currencies):
        currency = driver.find_element(
            By.ID,
            f"ctl00_ContentPlaceHolder2_Repeater1_ctl0{nth}_lblMtbea"
        ).get_attribute("innerText")

        value = clean_float(driver.find_element(
            by=By.CSS_SELECTOR,
            value=f"#ctl00_ContentPlaceHolder2_Repeater1_ctl0"
                  f"{nth}_grvDelayedCheque_ctl00__1 > td:nth-child("
                  f"2)").get_attribute(
            "innerText"))
        if "דולר" in currency:
            result.usd = value
        elif "אירו" in currency:
            result.eur = value
    driver.switch_to.default_content()

    safe_click(driver, find_element_by_text(
        driver,
        By.CSS_SELECTOR,
        "ul.sub-menu-items > li > a",
        "תנועות בחשבון"
    ))
    driver.implicitly_wait(10)
    driver.switch_to.frame("contentFrame")
    start_date = driver.find_element(
        By.ID,
        "ctl00_ContentPlaceHolder2_SkyDateRangePicker1_SkyDatePicker1ID_"
        "radDatePickerID_dateInput"
    )
    start_date.send_keys(Keys.CONTROL + "a")
    start_date.send_keys("01/01/2021")
    start_date.send_keys(Keys.RETURN)

    currencies = {
        'דולר': 'usd',
        'אירו': 'eur',
    }
    driver.implicitly_wait(10)
    for n in (0, 4):
        header_elements = driver.find_elements(
            By.ID,
            f'ctl00_ContentPlaceHolder2_Repeater1_ctl0{n}'
            f'_ctl00_ContentPlaceHolder2_Repeater1_ctl0{n}_PageAjaxPanel1Panel'
        )
        if not header_elements:
            continue
        currency = WebDriverWait(driver, 10).until(
            ec.visibility_of_element_located((
                By.ID,
                f'ctl00_ContentPlaceHolder2_Repeater1_ctl0{n}_lblShemMatbea'
            ))
        ).text
        for row in header_elements[0].find_elements(By.CSS_SELECTOR, 'tr'):
            cells = row.get_property('cells')
            if len(cells) != 6:
                continue
            result.transactions[currencies[currency]].append(
                {
                    'date': cells[0].text,
                    'value_date': cells[1].text,
                    'description': cells[2].text,
                    'serial': cells[3].text,
                    'value': cells[4].text,
                    'balance': cells[5].text,
                }
            )
    driver.switch_to.default_content()


def process_stocks(driver: WebDriver, result: ScrapeResults):
    driver.implicitly_wait(10)
    safe_click(driver, driver.find_element(
        by=By.CSS_SELECTOR,
        value="#mainMenu > ul > li:nth-child(5) > a"
    ))  # שוק ההון
    try:
        driver.find_element(By.CLASS_NAME, "miz-notification-messages")
    except NoSuchElementException:
        return
    for tr in driver.find_elements(by=By.CSS_SELECTOR,
                                   value="tr.k-master-row"):
        stock_dump = tr.get_attribute("innerText").split("\n")
        if len(stock_dump) < 15:
            continue
        result.stocks.append({
            "fullName": stock_dump[1],
            "bankSymbol": stock_dump[2],
            "price": clean_float(stock_dump[4]),
            "quantity": clean_float(stock_dump[8]),
            "profitPercent": clean_float(stock_dump[13]),
            "profitNis": clean_float(stock_dump[14]),
        })
