from os import environ

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, \
    WebDriverException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By

from scraper.common import ScrapeResults, find_element_by_text, safe_click, \
    clean_float


def scrape(target, capabilities):
    result = ScrapeResults()
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


def scrape_detect_login(driver):
    login_button = driver.find_element(by=By.ID, value="logInBtn")
    assert login_button.text == "כניסה לחשבון"
    safe_click(driver, login_button)


def scrape_perform_login(driver):
    driver.implicitly_wait(2)
    for _ in range(60):
        try:
            driver.find_element(by=By.CLASS_NAME, value="sk-ball-spin")
        except NoSuchElementException:
            break

    driver.switch_to.frame(
        driver.find_element(by=By.CSS_SELECTOR, value="iframe"))
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


def scrape_process(driver, result):
    driver.implicitly_wait(5)
    exit_button = None

    for _ in range(60):
        try:
            exit_button = driver.find_element(
                by=By.CLASS_NAME,
                value="lnkExitWebSite",
            )
            break
        except NoSuchElementException:
            pass
    try:
        try:
            safe_click(driver, driver.find_element(
                by=By.ID,
                value="ctl00_ContentPlaceHolder2_btnSave",
            ))
        except NoSuchElementException:
            pass

        safe_click(driver, driver.find_element(
            by=By.CSS_SELECTOR,
            value="#mainMenu > ul > li:nth-child(2) > a"
        ))  # עובר ושב
        nis_balance = find_element_by_text(driver, By.CLASS_NAME, "sky-big3",
                                           "₪", exact=False)
        result.nis = clean_float(nis_balance.text)

        safe_click(driver, find_element_by_text(driver, By.CLASS_NAME,
                                                "sub-menu-parent",
                                                "עו''ש מט''ח"))
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
            driver.find_element(by=By.CLASS_NAME, value="error_msg")
        except NoSuchElementException:
            driver.implicitly_wait(10)
            driver.switch_to.frame("contentFrame")
            currencies = len(driver.find_elements(by=By.CLASS_NAME, value="header3")) - 1
            for nth in range(0, currencies):
                currency = driver.find_element(
                    by=By.ID,
                    value=f"ctl00_ContentPlaceHolder2_Repeater1_ctl0{nth}_lblMtbea"
                ).get_attribute("innerText")
                value = clean_float(driver.find_element(
                    by=By.CSS_SELECTOR,
                    value=f"#ctl00_ContentPlaceHolder2_Repeater1_ctl0{nth}_grvDelayedCheque_ctl00__1 > td:nth-child(2)").get_attribute("innerText"))
                if "דולר" in currency:
                    result.usd = value
                elif "אירו" in currency:
                    result.eur = value
            driver.switch_to.default_content()

        driver.implicitly_wait(30)
        safe_click(driver, driver.find_element(
            by=By.CSS_SELECTOR,
            value="#mainMenu > ul > li:nth-child(5) > a"
        ))  # שוק ההון

        try:
            driver.find_element(
                by=By.CLASS_NAME,
                value="miz-notification-messages"
            )
        except NoSuchElementException:
            return result

        for tr in driver.find_elements(by=By.CSS_SELECTOR, value="tr.k-master-row"):
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
